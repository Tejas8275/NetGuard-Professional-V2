"""Password hashing and verification for locally registered users."""
import hashlib
import hmac
import re
import os

PASSWORD_SCRYPT_N = 2 ** 14
PASSWORD_SCRYPT_R = 8
PASSWORD_SCRYPT_P = 1

# Actions that actively probe devices or generate security findings are limited
# to the local administrator. Read-only diagnostics remain available to Viewer
# accounts so they can inspect the workstation without starting a network scan.
ADMIN_ACTIONS = frozenset({'network_scan', 'security_scan'})


def password_hash(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(
        password.encode('utf-8'), salt=salt,
        n=PASSWORD_SCRYPT_N, r=PASSWORD_SCRYPT_R, p=PASSWORD_SCRYPT_P, dklen=32
    )
    return salt.hex(), digest.hex()


def verify_password(password, salt_hex, expected_hash):
    """Verify a password using a constant-time hash comparison."""
    try:
        _, actual_hash = password_hash(password, bytes.fromhex(salt_hex))
        return hmac.compare_digest(actual_hash, expected_hash)
    except (TypeError, ValueError):
        return False


def valid_password(password):
    return (
        len(password) >= 12
        and bool(re.search(r'[A-Z]', password))
        and bool(re.search(r'[a-z]', password))
        and bool(re.search(r'\d', password))
        and bool(re.search(r'[^A-Za-z0-9]', password))
    )


def can_perform(role, action):
    """Return whether a stored local role may perform an application action."""
    if action not in ADMIN_ACTIONS:
        return True
    return str(role or '').strip().lower() == 'admin'
