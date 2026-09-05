import unittest

from core.security import calculate_risk, parse_open_ports, security_findings_for_ports


class SecurityParsingTests(unittest.TestCase):
    def test_display_values_are_normalized_to_port_numbers(self):
        self.assertEqual(parse_open_ports('22 (SSH), 3389 (RDP)'), [22, 3389])

    def test_no_exposed_services_has_zero_risk(self):
        self.assertEqual(calculate_risk('No exposed services'), 'LOW (0)')

    def test_friendly_port_labels_receive_their_real_risk_weight(self):
        self.assertEqual(calculate_risk('22 (SSH), 3389 (RDP)'), 'MEDIUM (50)')

    def test_security_findings_accept_friendly_port_labels(self):
        findings = security_findings_for_ports('23 (Telnet), 443 (HTTPS)')
        self.assertEqual(findings[0][0], 'CRITICAL')
        self.assertEqual(findings[0][2], '23')
        self.assertEqual(findings[1][0], 'INFO')
        self.assertEqual(findings[1][2], '443')
