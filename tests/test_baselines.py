import unittest

from core.baselines import normalize_baseline_name, normalize_baselines, save_baseline


class BaselineTests(unittest.TestCase):
    def test_baseline_name_is_trimmed_and_bounded(self):
        self.assertEqual(normalize_baseline_name('  Office   trusted  '), 'Office trusted')
        with self.assertRaises(ValueError):
            normalize_baseline_name('')

    def test_saved_baseline_copies_scan_snapshot(self):
        devices = [{'ip': '192.168.1.2', 'mac': 'AA:BB:CC:00:00:01'}]
        baselines = save_baseline({}, 'Office', devices, '2026-09-05 16:30:00')
        devices[0]['ip'] = '192.168.1.99'
        self.assertEqual(baselines['Office']['devices'][0]['ip'], '192.168.1.2')
        self.assertEqual(normalize_baselines({'bad': {'devices': 'wrong'}}), {})
