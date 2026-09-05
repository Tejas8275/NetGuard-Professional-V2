"""Bounded, cancellable worker orchestration for authorized local scans."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

DEFAULT_SCAN_WORKERS = 8

SCAN_PROFILES = {
    'Quick Discovery': {'max_workers': 16, 'resolve_hostname': False, 'scan_ports': False},
    'Standard': {'max_workers': 8, 'resolve_hostname': True, 'scan_ports': True},
    'Deep Analysis': {'max_workers': 4, 'resolve_hostname': True, 'scan_ports': True},
}


def scan_profile(name):
    """Return a safe, named scan profile; unknown values fall back to Standard."""
    return dict(SCAN_PROFILES.get(str(name), SCAN_PROFILES['Standard']))


def scan_subnet(prefix, probe_host, cancellation_event, max_workers=DEFAULT_SCAN_WORKERS, host_indexes=range(1, 255)):
    """Yield ``(completed, host_index, result)`` as local hosts finish.

    ``probe_host`` owns the actual network work. This helper only controls
    bounded concurrency and cancellation, keeping Tkinter out of workers.
    """
    max_workers = max(1, min(int(max_workers), 32))
    host_indexes = iter(host_indexes)

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='netguard-scan') as executor:
        futures = {}

        def submit_next():
            """Keep the queued work bounded so cancellation takes effect promptly."""
            if cancellation_event.is_set():
                return False
            try:
                index = next(host_indexes)
            except StopIteration:
                return False
            futures[executor.submit(probe_host, f'{prefix}{index}')] = index
            return True

        for _ in range(max_workers):
            if not submit_next():
                break

        completed = 0
        while futures:
            done, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in done:
                index = futures.pop(future)
                if cancellation_event.is_set():
                    for pending in futures:
                        pending.cancel()
                    return
                completed += 1
                try:
                    result = future.result()
                except Exception:
                    result = None
                yield completed, index, result
                submit_next()
