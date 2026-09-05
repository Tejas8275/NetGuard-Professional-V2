import unittest

from core.network_core import is_private_scan_prefix


class PrivateScanScopeTests(unittest.TestCase):
    def test_all_supported_private_ranges_are_allowed(self):
        for prefix in ('10.42.8.', '172.20.1.', '192.168.50.'):
            with self.subTest(prefix=prefix):
                self.assertTrue(is_private_scan_prefix(prefix))

    def test_public_reserved_and_invalid_ranges_are_rejected(self):
        for prefix in ('8.8.8.', '172.15.1.', '172.32.1.', '192.0.2.', '169.254.1.', '192.168.999.', '192.168.'):
            with self.subTest(prefix=prefix):
                self.assertFalse(is_private_scan_prefix(prefix))
