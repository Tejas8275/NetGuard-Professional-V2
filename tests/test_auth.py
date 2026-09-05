import unittest

from core.auth import can_perform, password_hash, valid_password, verify_password
from core.recovery import AdminRecoveryError, administrator_usernames, reset_admin_password


class AuthenticationTests(unittest.TestCase):
    def test_password_verification_uses_stored_salt_and_hash(self):
        salt, digest = password_hash('NetGuard!2026')
        self.assertTrue(verify_password('NetGuard!2026', salt, digest))
        self.assertFalse(verify_password('not-the-password', salt, digest))

    def test_password_policy_requires_length_and_character_variety(self):
        self.assertTrue(valid_password('NetGuard!2026'))
        self.assertFalse(valid_password('Short1!'))
        self.assertFalse(valid_password('netguardpassword1!'))
        self.assertFalse(valid_password('NETGUARDPASSWORD1!'))
        self.assertFalse(valid_password('NetGuardPassword1'))

    def test_only_administrators_can_run_active_security_operations(self):
        for action in ('network_scan', 'security_scan'):
            with self.subTest(action=action):
                self.assertTrue(can_perform('Admin', action))
                self.assertFalse(can_perform('Viewer', action))
                self.assertFalse(can_perform(None, action))

    def test_read_only_actions_remain_available_to_viewers(self):
        self.assertTrue(can_perform('Viewer', 'health_scan'))

    def test_admin_password_recovery_rehashes_and_preserves_role(self):
        salt, digest = password_hash('Original!Password1')
        users = {
            'netadmin': {
                'username': 'NetAdmin', 'role': 'Admin', 'salt': salt, 'password_hash': digest,
                'created_at': '2026-09-05T00:00:00+00:00',
            },
            'viewer': {'username': 'Viewer', 'role': 'Viewer'},
        }

        updated = reset_admin_password(users, 'NETADMIN', 'Recovered!Password2', reset_at='2026-09-05T12:00:00+00:00')

        self.assertEqual(administrator_usernames(users), ['NetAdmin'])
        self.assertEqual(updated['role'], 'Admin')
        self.assertNotEqual(updated['password_hash'], digest)
        self.assertTrue(verify_password('Recovered!Password2', updated['salt'], updated['password_hash']))
        self.assertFalse(verify_password('Original!Password1', updated['salt'], updated['password_hash']))
        self.assertEqual(updated['password_reset_at'], '2026-09-05T12:00:00+00:00')

    def test_recovery_rejects_non_admin_and_weak_passwords(self):
        users = {'viewer': {'username': 'Viewer', 'role': 'Viewer'}}
        with self.assertRaises(AdminRecoveryError):
            reset_admin_password(users, 'viewer', 'Recovered!Password2')
        users['admin'] = {'username': 'Admin', 'role': 'Admin'}
        with self.assertRaises(AdminRecoveryError):
            reset_admin_password(users, 'admin', 'short')

    def test_explicit_recovery_can_promote_existing_user_when_no_admin_exists(self):
        salt, digest = password_hash('Original!Password1')
        users = {'tejas': {'username': 'Tejas', 'role': 'Analyst', 'salt': salt, 'password_hash': digest}}

        updated = reset_admin_password(
            users, 'tejas', 'Recovered!Password2', reset_at='2026-09-05T12:00:00+00:00', promote_existing=True
        )

        self.assertEqual(updated['role'], 'Admin')
        self.assertEqual(updated['role_promoted_at'], '2026-09-05T12:00:00+00:00')
        self.assertTrue(verify_password('Recovered!Password2', updated['salt'], updated['password_hash']))
        self.assertEqual(administrator_usernames(users), ['Tejas'])

    def test_promotion_recovery_is_rejected_when_an_admin_exists(self):
        users = {
            'admin': {'username': 'Admin', 'role': 'Admin'},
            'viewer': {'username': 'Viewer', 'role': 'Viewer'},
        }
        with self.assertRaises(AdminRecoveryError):
            reset_admin_password(users, 'viewer', 'Recovered!Password2', promote_existing=True)
