import unittest

from core.scan_comparison import (
    compare_scans, comparison_report_lines, comparison_statuses, comparison_summary,
)


class ScanComparisonTests(unittest.TestCase):
    def test_identifies_new_gone_and_changed_devices(self):
        previous = [
            {'ip': '192.168.1.2', 'mac': 'AA:BB:CC:00:00:01', 'hostname': 'router', 'ports': '80 (HTTP)', 'risk': 'LOW (5)'},
            {'ip': '192.168.1.3', 'mac': 'AA:BB:CC:00:00:02', 'hostname': 'old', 'ports': 'None', 'risk': 'LOW (0)'},
        ]
        current = [
            {'ip': '192.168.1.2', 'mac': 'AA:BB:CC:00:00:01', 'hostname': 'router', 'ports': '22 (SSH)', 'risk': 'MEDIUM (15)'},
            {'ip': '192.168.1.4', 'mac': 'AA:BB:CC:00:00:03', 'hostname': 'new', 'ports': 'None', 'risk': 'LOW (0)'},
        ]
        comparison = compare_scans(previous, current)
        self.assertEqual(comparison['new'][0]['ip'], '192.168.1.4')
        self.assertEqual(comparison['gone'][0]['ip'], '192.168.1.3')
        self.assertEqual(comparison['changed'][0]['fields'], ['ports', 'risk'])
        self.assertEqual(comparison_summary(comparison), 'New: 1 • Gone: 1 • Changed: 1')
        statuses = comparison_statuses(comparison)
        self.assertEqual(statuses['MAC:AA:BB:CC:00:00:03'], 'NEW')
        self.assertEqual(statuses['MAC:AA:BB:CC:00:00:01'], 'CHANGED: ports, risk')
        report = '\n'.join(comparison_report_lines(comparison))
        self.assertIn('New devices:', report)
        self.assertIn('Devices no longer seen:', report)
        self.assertIn('Changed devices:', report)

    def test_empty_comparison_has_clear_export_text(self):
        comparison = {'new': [], 'gone': [], 'changed': []}
        self.assertEqual(comparison_statuses(comparison), {})
        self.assertEqual(
            comparison_report_lines(comparison),
            ['New: 0 • Gone: 0 • Changed: 0', 'No device changes detected.'],
        )
