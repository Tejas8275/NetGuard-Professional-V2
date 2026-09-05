"""Versioned, atomic local persistence for NetGuard."""
import json
import os
from pathlib import Path

APP_NAME = 'NetGuard Professional'
STATE_SCHEMA_VERSION = 1


def _app_data_dir():
    """Return the per-user application-data directory without side effects."""
    root = Path(os.environ.get('LOCALAPPDATA') or os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share')
    return root / APP_NAME


APP_DATA_DIR = _app_data_dir()
APP_DATA_FILE = APP_DATA_DIR / 'state.json'
USER_DB_FILE = APP_DATA_DIR / 'users.json'
LEGACY_APP_DATA_FILE = Path.home() / '.netguard_pro_data.json'
LEGACY_USER_DB_FILE = Path.home() / '.netguard_pro_users.json'


def _read_json(path, default):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, type(default)) else default
    except (OSError, json.JSONDecodeError):
        return default


def _atomic_write(path, data):
    """Write JSON through a same-directory temporary file then replace it."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != 'nt':
        path.parent.chmod(0o700)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def load_users():
    """Load password-hash records and transparently migrate the legacy file."""
    users = _read_json(USER_DB_FILE, {})
    if users or USER_DB_FILE.exists():
        return users
    legacy_users = _read_json(LEGACY_USER_DB_FILE, {})
    if legacy_users:
        save_users(legacy_users)
    return legacy_users


def save_users(users):
    _atomic_write(USER_DB_FILE, users)


def load_app_state():
    """Load the current state document, migrating the old flat JSON once."""
    data = _read_json(APP_DATA_FILE, {})
    if data:
        return data
    legacy_data = _read_json(LEGACY_APP_DATA_FILE, {})
    if legacy_data:
        save_app_state(legacy_data)
    return legacy_data


def save_app_state(state):
    payload = dict(state)
    payload['schema_version'] = STATE_SCHEMA_VERSION
    _atomic_write(APP_DATA_FILE, payload)
