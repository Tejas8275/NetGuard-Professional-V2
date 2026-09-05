"""Pure comparison helpers for consecutive local network scan snapshots."""


def device_identity(device):
    mac = str(device.get('mac', 'Unknown')).upper()
    return f'MAC:{mac}' if mac != 'UNKNOWN' else f'IP:{device.get("ip", "")}'


def compare_scans(previous, current):
    """Return new, gone, and materially changed devices between snapshots."""
    before = {device_identity(device): device for device in previous}
    after = {device_identity(device): device for device in current}
    changed = []
    for key in before.keys() & after.keys():
        fields = [field for field in ('hostname', 'ports', 'risk') if str(before[key].get(field, '')) != str(after[key].get(field, ''))]
        if fields:
            changed.append({'key': key, 'fields': fields, 'before': before[key], 'after': after[key]})
    return {
        'new': [after[key] for key in after.keys() - before.keys()],
        'gone': [before[key] for key in before.keys() - after.keys()],
        'changed': changed,
    }


def comparison_summary(comparison):
    return f"New: {len(comparison['new'])} • Gone: {len(comparison['gone'])} • Changed: {len(comparison['changed'])}"


def comparison_statuses(comparison):
    """Return current-device comparison labels keyed by stable device identity."""
    statuses = {}
    for device in comparison.get('new', []):
        statuses[device_identity(device)] = 'NEW'
    for change in comparison.get('changed', []):
        fields = ', '.join(change.get('fields', []))
        statuses[str(change.get('key', ''))] = f'CHANGED: {fields}' if fields else 'CHANGED'
    return statuses


def _device_label(device):
    hostname = str(device.get('hostname', '')).strip()
    ip_address = str(device.get('ip', '')).strip()
    return f'{hostname} ({ip_address})' if hostname and hostname != ip_address else ip_address or 'Unknown device'


def comparison_report_lines(comparison):
    """Format a readable, detailed latest-scan comparison for exported reports."""
    lines = [comparison_summary(comparison)]
    for title, key in (('New devices', 'new'), ('Devices no longer seen', 'gone')):
        devices = comparison.get(key, [])
        if devices:
            lines.append(f'{title}:')
            lines.extend(f'  - {_device_label(device)}' for device in devices)
    changes = comparison.get('changed', [])
    if changes:
        lines.append('Changed devices:')
        for change in changes:
            fields = ', '.join(change.get('fields', [])) or 'details'
            lines.append(f"  - {_device_label(change.get('after', {}))}: {fields}")
    if len(lines) == 1:
        lines.append('No device changes detected.')
    return lines
