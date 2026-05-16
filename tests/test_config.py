"""Tests for Config — particularly the env-var override mechanism."""

from __future__ import annotations

import os

import pytest

from app.core.config import Config


class TestDefaults:
    def test_default_thresholds_sensible(self):
        cfg = Config()
        assert 10 <= cfg.click_threshold_px <= 100
        assert 0.0 <= cfg.smoothing_factor <= 1.0
        assert 0.0 <= cfg.min_detection_confidence <= 1.0


class TestWithOverrides:
    def test_override_returns_new_config(self):
        original = Config()
        modified = original.with_overrides(click_threshold_px=50)
        assert modified.click_threshold_px == 50
        assert original.click_threshold_px == 30  # unchanged (frozen dataclass)

    def test_multiple_overrides(self):
        cfg = Config().with_overrides(camera_index=2, smoothing_factor=0.5)
        assert cfg.camera_index == 2
        assert cfg.smoothing_factor == 0.5


class TestFromEnv:
    @pytest.fixture(autouse=True)
    def _cleanup_env(self):
        """Strip any VM_* env vars before each test, restore after."""
        saved = {k: v for k, v in os.environ.items() if k.startswith("VM_")}
        for k in list(os.environ):
            if k.startswith("VM_"):
                del os.environ[k]
        yield
        for k in list(os.environ):
            if k.startswith("VM_"):
                del os.environ[k]
        os.environ.update(saved)

    def test_no_env_vars_returns_defaults(self):
        cfg = Config.from_env()
        assert cfg.click_threshold_px == Config().click_threshold_px

    def test_int_env_var_applied(self):
        os.environ["VM_CLICK_THRESHOLD_PX"] = "42"
        cfg = Config.from_env()
        assert cfg.click_threshold_px == 42

    def test_float_env_var_applied(self):
        os.environ["VM_SMOOTHING_FACTOR"] = "0.7"
        cfg = Config.from_env()
        assert cfg.smoothing_factor == 0.7

    def test_bool_env_var_applied(self):
        os.environ["VM_SHOW_LANDMARKS"] = "false"
        cfg = Config.from_env()
        assert cfg.show_landmarks is False

    @pytest.mark.parametrize("value", ["1", "true", "True", "yes", "on", "YES"])
    def test_bool_truthy_values(self, value):
        os.environ["VM_SHOW_FPS_OVERLAY"] = value
        cfg = Config.from_env()
        assert cfg.show_fps_overlay is True

    def test_invalid_value_silently_ignored(self):
        """Bad config values shouldn't crash the app — fall back to defaults."""
        os.environ["VM_CLICK_THRESHOLD_PX"] = "not-a-number"
        cfg = Config.from_env()
        assert cfg.click_threshold_px == Config().click_threshold_px
