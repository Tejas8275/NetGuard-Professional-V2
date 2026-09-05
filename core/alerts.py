"""Pure alert-record operations for the incident queue and its filtered UI."""


def normalize_alert_rows(rows):
    """Return serializable four-column alert rows, ignoring malformed entries."""
    return [list(row[:4]) for row in rows if isinstance(row, (list, tuple)) and len(row) >= 4]


def filtered_alert_rows(rows, severity):
    """Return matching rows without changing the canonical incident collection."""
    wanted = str(severity or 'ALL')
    return [(index, row) for index, row in enumerate(rows) if wanted == 'ALL' or str(row[1]) == wanted]


def acknowledge_alert_rows(rows, indexes):
    """Acknowledge selected alert indexes in place and return the update count."""
    changed = 0
    for index in sorted(set(indexes)):
        if not isinstance(index, int) or index < 0 or index >= len(rows):
            continue
        row = rows[index]
        if str(row[1]) == 'ACK':
            continue
        row[1] = 'ACK'
        if not str(row[2]).startswith('[ACKNOWLEDGED] '):
            row[2] = '[ACKNOWLEDGED] ' + str(row[2])
        changed += 1
    return changed


def remove_acknowledged_alert_rows(rows):
    """Return unacknowledged rows and how many acknowledged rows were removed."""
    kept = [row for row in rows if str(row[1]) != 'ACK']
    return kept, len(rows) - len(kept)
