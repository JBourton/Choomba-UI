"""
Tests for the settings plumbing: the APP_SETTINGS section in backend/config.py,
the detector's live updates and the daemon's get_settings / set_settings
commands.
"""

import os
import unittest

from backend import config
from backend.detector.clap_detector import DoubleClapDetector
from backend.service import ActivationService


class TestAppSettingsSection(unittest.TestCase):
    """backend/config.py holds the knobs in one clearly marked place."""

    def test_app_settings_exist_and_have_sane_defaults(self):
        self.assertIsInstance(config.APP_SETTINGS, dict)
        for key in (
            "clap_sensitivity",
            "clap_ratio_sensitive",
            "clap_ratio_strict",
            "clap_min_low_band_share",
            "clap_min_crack_band_share",
            "clap_min_interval_ms",
            "clap_max_interval_ms",
            "clap_pair_confirmation_ms",
            "clap_max_transient_duration_ms",
            "clap_cooldown_ms",
            "clap_min_peak_threshold",
            "sample_rate",
            "chunk_size",
            "host",
            "port",
        ):
            self.assertIn(key, config.APP_SETTINGS, f"missing app setting: {key}")

    def test_ui_editable_settings_are_a_subset(self):
        for key in config.UI_EDITABLE_SETTINGS:
            self.assertIn(key, config.APP_SETTINGS)

    def test_ratio_range_is_ordered(self):
        self.assertLess(
            config.APP_SETTINGS["clap_ratio_sensitive"],
            config.APP_SETTINGS["clap_ratio_strict"],
        )

    def test_band_share_thresholds_are_in_range(self):
        for key in ("clap_min_low_band_share", "clap_min_crack_band_share"):
            value = config.APP_SETTINGS[key]
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_environment_overrides_are_applied(self):
        os.environ["CHOOMBA_CLAP_MIN_LOW_BAND_SHARE"] = "0.77"
        try:
            import importlib
            importlib.reload(config)
            self.assertAlmostEqual(
                config.APP_SETTINGS["clap_min_low_band_share"], 0.77
            )
        finally:
            del os.environ["CHOOMBA_CLAP_MIN_LOW_BAND_SHARE"]
            import importlib
            importlib.reload(config)


class TestDetectorSettings(unittest.TestCase):
    """The detector reacts to a settings patch."""

    def setUp(self):
        self.detector = DoubleClapDetector()
        self.detector.start()

    def test_sensitivity_moves_the_detection_ratio(self):
        self.detector.set_sensitivity(0.1)
        strict = self.detector.current_detection_ratio()
        self.detector.set_sensitivity(1.0)
        sensitive = self.detector.current_detection_ratio()
        self.assertGreater(strict, sensitive,
                           "lower sensitivity must demand a louder clap")

    def test_apply_settings_updates_the_ratio(self):
        before = self.detector.current_detection_ratio()
        self.detector.apply_settings({"clap_sensitivity": 0.1})
        self.assertGreater(self.detector.current_detection_ratio(), before)

    def test_apply_settings_updates_the_band_shares(self):
        self.detector.apply_settings({"clap_min_low_band_share": 0.5})
        self.assertAlmostEqual(self.detector.min_low_band_share, 0.5)
        self.detector.apply_settings({"clap_min_crack_band_share": 0.25})
        self.assertAlmostEqual(self.detector.min_crack_band_share, 0.25)

    def test_apply_settings_clamps_out_of_range_values(self):
        self.detector.apply_settings({"clap_min_low_band_share": 5.0})
        self.assertLessEqual(self.detector.min_low_band_share, 0.9)
        self.detector.apply_settings({"clap_min_low_band_share": -1.0})
        self.assertGreaterEqual(self.detector.min_low_band_share, 0.0)

    def test_apply_settings_keeps_the_tempo_window_consistent(self):
        self.detector.apply_settings({"clap_max_interval_ms": 200.0})
        self.assertAlmostEqual(self.detector.max_clap_interval_ms, 200.0)
        self.detector.apply_settings({"clap_min_interval_ms": 900.0})
        self.assertLess(
            self.detector.min_clap_interval_ms, self.detector.max_clap_interval_ms
        )


class TestServiceSettings(unittest.TestCase):
    """The daemon exposes the settings and applies the ones the UI may change."""

    def setUp(self):
        self.service = ActivationService(use_mock_audio=True)

    def test_get_settings_reports_the_current_values(self):
        settings = self.service.get_settings()
        for key in (
            "clap_sensitivity",
            "clap_min_low_band_share",
            "clap_min_crack_band_share",
            "clap_max_interval_ms",
            "detection_ratio",
        ):
            self.assertIn(key, settings)

    def test_set_settings_applies_editable_values(self):
        applied = self.service.apply_settings({
            "clap_sensitivity": 0.3,
            "clap_min_low_band_share": 0.5,
        })
        self.assertIn("clap_sensitivity", applied)
        self.assertAlmostEqual(self.service.detector.sensitivity, 0.3)
        self.assertAlmostEqual(self.service.detector.min_low_band_share, 0.5)

    def test_set_settings_ignores_values_that_are_not_editable(self):
        applied = self.service.apply_settings({
            "clap_max_transient_duration_ms": 5.0,
            "sample_rate": 8000,
        })
        self.assertEqual(applied, {})
        self.assertNotEqual(
            self.service.detector.max_transient_duration_ms, 5.0
        )

    def test_set_settings_ignores_garbage(self):
        applied = self.service.apply_settings({"clap_sensitivity": "not a number"})
        self.assertEqual(applied, {})


if __name__ == "__main__":
    unittest.main()
