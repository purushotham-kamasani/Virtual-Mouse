"""Tests for the CLI argument parser."""

from __future__ import annotations

import pytest

from app.main import parse_args


class TestArgParse:
    def test_defaults(self):
        args = parse_args([])
        assert args.camera == 0
        assert args.click_threshold is None
        assert args.smoothing is None
        assert args.calibrate is False
        assert args.no_window is False

    def test_camera_index(self):
        args = parse_args(["--camera", "2"])
        assert args.camera == 2

    def test_click_threshold(self):
        args = parse_args(["--click-threshold", "45"])
        assert args.click_threshold == 45

    def test_smoothing(self):
        args = parse_args(["--smoothing", "0.5"])
        assert args.smoothing == 0.5

    def test_calibrate_flag(self):
        args = parse_args(["--calibrate"])
        assert args.calibrate is True

    def test_no_window_flag(self):
        args = parse_args(["--no-window"])
        assert args.no_window is True

    def test_help_exits_cleanly(self):
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--help"])
        assert exc_info.value.code == 0

    def test_invalid_arg_exits_with_error(self):
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--bogus"])
        assert exc_info.value.code != 0
