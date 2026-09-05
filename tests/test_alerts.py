import unittest

from core.alerts import (
    acknowledge_alert_rows, filtered_alert_rows, normalize_alert_rows, remove_acknowledged_alert_rows,
)


class AlertRecordTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            ['10:00:00', 'CRITICAL', 'Packet loss high', 'Monitor'],
            ['10:01:00', 'LOW', 'DNS check warning', 'Health Scan'],
            ['10:02:00', 'HIGH', 'RDP exposed', 'Security Center'],
        ]

    def test_filtering_keeps_the_canonical_incident_rows_intact(self):
        filtered = filtered_alert_rows(self.rows, 'HIGH')
        self.assertEqual(filtered, [(2, self.rows[2])])
        self.assertEqual(len(self.rows), 3)
        self.assertEqual(self.rows[0][1], 'CRITICAL')

    def test_warning_incidents_are_filterable_as_a_first_class_severity(self):
        self.rows.append(['10:03:00', 'WARNING', 'New device discovered', 'Network Scanner'])
        self.assertEqual(filtered_alert_rows(self.rows, 'WARNING'), [(3, self.rows[3])])

    def test_acknowledgement_and_cleanup_target_canonical_rows(self):
        self.assertEqual(acknowledge_alert_rows(self.rows, [2]), 1)
        self.assertEqual(self.rows[2][1], 'ACK')
        remaining, removed = remove_acknowledged_alert_rows(self.rows)
        self.assertEqual(removed, 1)
        self.assertEqual([row[1] for row in remaining], ['CRITICAL', 'LOW'])

    def test_normalization_discards_malformed_persisted_rows(self):
        rows = normalize_alert_rows([self.rows[0], ['too', 'short'], 'invalid'])
        self.assertEqual(rows, [self.rows[0]])
