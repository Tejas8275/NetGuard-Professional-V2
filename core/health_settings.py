"""Validation and defaults for local network-health thresholds."""

DEFAULT_HEALTH_THRESHOLDS = {
    'latency_warning_ms': 100.0,
    'latency_critical_ms': 200.0,
    'packet_loss_warning_pct': 5.0,
    'packet_loss_critical_pct': 20.0,
}


def normalize_health_thresholds(values=None):
    """Return validated thresholds while preserving the established defaults."""
    values = values or {}
    result = {}
    for key, default in DEFAULT_HEALTH_THRESHOLDS.items():
        try:
            value = float(values.get(key, default))
        except (TypeError, ValueError):
            raise ValueError(f'{key} must be a number.') from None
        if value <= 0:
            raise ValueError(f'{key} must be greater than zero.')
        result[key] = value
    if result['latency_warning_ms'] >= result['latency_critical_ms']:
        raise ValueError('Latency warning threshold must be lower than the critical threshold.')
    if result['packet_loss_warning_pct'] >= result['packet_loss_critical_pct']:
        raise ValueError('Packet-loss warning threshold must be lower than the critical threshold.')
    if result['packet_loss_critical_pct'] > 100:
        raise ValueError('Packet-loss critical threshold cannot exceed 100%.')
    return result
