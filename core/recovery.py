"""Local administrator password-recovery helpers.

This module deliberately has no GUI or command-line dependencies so that the
same validation and hashing rules are used by the recovery command and tests.
"""
from datetime import datetime

from core.auth import password_hash, valid_password


class AdminRecoveryError(ValueError):
    """Raised when a local administrator password cannot be reset safely."""


def administrator_usernames(users):
    """Return administrator names from a loaded local user document."""
    return sorted(
        str(record.get('username', key))
        for key, record in users.items()
        if isinstance(record, dict) and str(record.get('role', '')).strip().lower() == 'admin'
    )


def reset_admin_password(users, username, new_password, reset_at=None, promote_existing=False):
    """Replace an existing administrator password with a freshly salted hash.

    ``users`` is updated in place but is not written to disk here. Callers must
    use ``core.storage.save_users`` so the existing atomic-write behaviour is
    preserved.
    """
    key = str(username or '').strip().lower()
    record = users.get(key)
    if not isinstance(record, dict):
        raise AdminRecoveryError('No matching local user was found.')
    if promote_existing and administrator_usernames(users):
        raise AdminRecoveryError('An Administrator account already exists; promotion recovery is unavailable.')
    is_administrator = str(record.get('role', '')).strip().lower() == 'admin'
    if not is_administrator and not promote_existing:
        raise AdminRecoveryError('The selected user is not an Administrator account.')
    if not valid_password(new_password):
        raise AdminRecoveryError(
            'Password must be at least 12 characters and include uppercase, lowercase, number, and symbol.'
        )

    salt, digest = password_hash(new_password)
    record['salt'] = salt
    record['password_hash'] = digest
    if not is_administrator:
        record['role'] = 'Admin'
        record['role_promoted_at'] = reset_at or datetime.now().astimezone().isoformat(timespec='seconds')
    record['password_reset_at'] = reset_at or datetime.now().astimezone().isoformat(timespec='seconds')
    return record
