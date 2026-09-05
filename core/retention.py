"""Validation and trimming helpers for locally retained operational records."""

DEFAULT_RETENTION_LIMITS = {'history': 200, 'alerts': 200}
RETENTION_LIMIT_OPTIONS = (100, 200, 500, 1000)


def normalize_retention_limits(values=None):
    """Return safe configured record limits, falling back per invalid value."""
    values = values or {}
    normalized = {}
    for key, default in DEFAULT_RETENTION_LIMITS.items():
        try:
            value = int(values.get(key, default))
        except (TypeError, ValueError):
            value = default
        normalized[key] = value if value in RETENTION_LIMIT_OPTIONS else default
    return normalized


def retain_latest(records, limit):
    """Keep the most recent records without mutating the caller's sequence."""
    return list(records)[-int(limit):]
