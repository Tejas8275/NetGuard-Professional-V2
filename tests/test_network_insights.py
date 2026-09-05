import unittest

from core.network_core import active_windows_adapter, detect_vpn, health_assessment, parse_windows_ipconfig


IPCONFIG_SAMPLE = """
Windows IP Configuration

Unknown adapter CloudflareWARP:

   Connection-specific DNS Suffix  . :
   IPv4 Address. . . . . . . . . . . : 172.16.0.2
   Default Gateway . . . . . . . . . : 172.16.0.1

Wireless LAN adapter Wi-Fi:

   Connection-specific DNS Suffix  . : home
   IPv4 Address. . . . . . . . . . . : 192.168.1.55
   Default Gateway . . . . . . . . . : fe80::1%18
                                       192.168.1.1
   DNS Servers . . . . . . . . . . . : fe80::1%18
                                       192.168.1.1
"""


class NetworkInsightsTests(unittest.TestCase):
    def test_adapter_parser_prefers_active_physical_adapter_and_ipv4_details(self):
        adapters = parse_windows_ipconfig(IPCONFIG_SAMPLE)
        self.assertEqual(len(adapters), 2)
        active = active_windows_adapter(IPCONFIG_SAMPLE)
        self.assertEqual(active['name'], 'Wi-Fi')
        self.assertEqual(active['ipv4'], '192.168.1.55')
        self.assertEqual(active['gateway'], '192.168.1.1')
        self.assertEqual(active['dns'], '192.168.1.1')

    def test_health_assessment_explains_https_only_connectivity(self):
        report = health_assessment(
            {'Local IP': '192.168.1.55', 'Adapter': 'Wi-Fi', 'Gateway': '192.168.1.1'},
            online=True,
            latency_ms=72,
            packet_loss=None,
            dns_ok=True,
        )
        self.assertEqual(report['score'], 95)
        self.assertEqual(report['status'], 'HEALTHY')
        self.assertTrue(any('ICMP packet loss' in insight for insight in report['insights']))

    def test_health_assessment_reports_actionable_missing_network_facts(self):
        report = health_assessment(
            {'Local IP': 'Unavailable', 'Adapter': 'Unavailable', 'Gateway': 'Unavailable'},
            online=False,
            latency_ms=None,
            packet_loss=None,
            dns_ok=False,
        )
        self.assertEqual(report['status'], 'PROBLEM')
        self.assertTrue(any('gateway' in insight.lower() for insight in report['insights']))

    def test_warp_tunnel_is_detected_without_replacing_the_physical_adapter(self):
        adapters = parse_windows_ipconfig(IPCONFIG_SAMPLE)
        vpn = detect_vpn(adapters, active_dns='127.0.2.2')
        self.assertTrue(vpn['active'])
        self.assertEqual(vpn['label'], 'WARP ACTIVE')
        self.assertEqual(active_windows_adapter(IPCONFIG_SAMPLE)['name'], 'Wi-Fi')

    def test_warp_dns_proxy_is_detected_when_the_adapter_name_is_not_available(self):
        vpn = detect_vpn([], active_dns='::ffff:127.0.2.2')
        self.assertTrue(vpn['active'])
        self.assertIn('DNS proxy', vpn['detail'])
