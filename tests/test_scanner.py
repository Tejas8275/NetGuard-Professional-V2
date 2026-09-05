import threading
import unittest

from core.scanner import scan_profile, scan_subnet


class ScannerOrchestrationTests(unittest.TestCase):
    def test_scan_profiles_use_safe_expected_capabilities(self):
        self.assertEqual(scan_profile('Quick Discovery')['max_workers'], 16)
        self.assertFalse(scan_profile('Quick Discovery')['scan_ports'])
        self.assertTrue(scan_profile('Standard')['scan_ports'])
        self.assertEqual(scan_profile('Deep Analysis')['max_workers'], 4)
        self.assertEqual(scan_profile('untrusted value'), scan_profile('Standard'))

    def test_scan_yields_each_completed_probe_result(self):
        cancelled = threading.Event()
        calls = []

        def probe(host):
            calls.append(host)
            return {'host': host}

        results = list(scan_subnet('192.168.1.', probe, cancelled, max_workers=2, host_indexes=range(1, 5)))
        self.assertEqual(len(results), 4)
        self.assertEqual({result[2]['host'] for result in results}, set(calls))
        self.assertEqual(sorted(result[0] for result in results), [1, 2, 3, 4])

    def test_cancelled_scan_stops_yielding_results(self):
        cancelled = threading.Event()
        calls = []

        def probe(host):
            calls.append(host)
            cancelled.set()
            return {'host': host}

        results = list(scan_subnet('10.0.0.', probe, cancelled, max_workers=1, host_indexes=range(1, 4)))
        self.assertEqual(results, [])
        self.assertEqual(calls, ['10.0.0.1'])
