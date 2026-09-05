"""Safe local storage helpers for named network-scan baselines."""
from copy import deepcopy


def normalize_baseline_name(value):
    name = ' '.join(str(value or '').split())
    if not 1 <= len(name) <= 60:
        raise ValueError('Baseline name must contain 1 to 60 characters.')
    return name


def normalize_baselines(values):
    """Discard malformed persisted baselines while preserving valid snapshots."""
    normalized = {}
    if not isinstance(values, dict):
        return normalized
    for raw_name, record in values.items():
        try:
            name = normalize_baseline_name(raw_name)
        except ValueError:
            continue
        if not isinstance(record, dict) or not isinstance(record.get('devices'), list):
            continue
        devices = [dict(device) for device in record['devices'] if isinstance(device, dict)]
        normalized[name] = {'created_at': str(record.get('created_at', 'Unknown')), 'devices': devices}
    return normalized


def save_baseline(baselines, name, devices, created_at):
    """Return a new baseline mapping with a snapshot independent of scan results."""
    saved = deepcopy(normalize_baselines(baselines))
    saved[normalize_baseline_name(name)] = {
        'created_at': str(created_at),
        'devices': [dict(device) for device in devices if isinstance(device, dict)],
    }
    return saved
