import unittest

from core.health_settings import DEFAULT_HEALTH_THRESHOLDS, normalize_health_thresholds
from core.network_core import health_assessment


class HealthSettingsTests(unittest.TestCase):
    def test_defaults_preserve_established_thresholds(self):
        self.assertEqual(normalize_health_thresholds(), DEFAULT_HEALTH_THRESHOLDS)

    def test_thresholds_require_ordered_positive_ranges(self):
        with self.assertRaises(ValueError):
            normalize_health_thresholds({'latency_warning_ms': 200, 'latency_critical_ms': 100})
        with self.assertRaises(ValueError):
            normalize_health_thresholds({'packet_loss_warning_pct': 20, 'packet_loss_critical_pct': 5})
        with self.assertRaises(ValueError):
            normalize_health_thresholds({'packet_loss_critical_pct': 101})

    def test_custom_thresholds_change_health_score_interpretation(self):
        network = {'Local IP': '192.168.1.55', 'Adapter': 'Wi-Fi', 'Gateway': '192.168.1.1'}
        default_report = health_assessment(network, True, 120, 1, True)
        custom_report = health_assessment(
            network, True, 120, 1, True,
            {'latency_warning_ms': 150, 'latency_critical_ms': 300, 'packet_loss_warning_pct': 10, 'packet_loss_critical_pct': 30},
        )
        self.assertEqual(default_report['score'], 96)
        self.assertEqual(custom_report['score'], 100)
