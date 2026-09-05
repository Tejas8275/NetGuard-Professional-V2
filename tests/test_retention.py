import unittest

from core.retention import DEFAULT_RETENTION_LIMITS, normalize_retention_limits, retain_latest


class RetentionTests(unittest.TestCase):
    def test_only_supported_local_record_limits_are_accepted(self):
        self.assertEqual(normalize_retention_limits({'history': '500', 'alerts': 100}), {'history': 500, 'alerts': 100})
        self.assertEqual(normalize_retention_limits({'history': '7', 'alerts': 'bad'}), DEFAULT_RETENTION_LIMITS)

    def test_retention_preserves_newest_records_without_mutating_input(self):
        records = ['first', 'second', 'third']
        self.assertEqual(retain_latest(records, 2), ['second', 'third'])
        self.assertEqual(records, ['first', 'second', 'third'])
