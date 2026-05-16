"""Tests for the pure-math geometry helpers."""

from __future__ import annotations

import math

import pytest

from app.tracking.geometry import Point2D, euclidean_distance, map_to_screen, smooth


class TestEuclideanDistance:
    def test_zero_when_same_point(self):
        p = Point2D(5.0, 5.0)
        assert euclidean_distance(p, p) == 0.0

    def test_simple_pythagorean_triple(self):
        a = Point2D(0.0, 0.0)
        b = Point2D(3.0, 4.0)
        assert euclidean_distance(a, b) == 5.0

    def test_symmetric(self):
        a, b = Point2D(1.0, 2.0), Point2D(7.0, 9.0)
        assert math.isclose(euclidean_distance(a, b), euclidean_distance(b, a))


class TestMapToScreen:
    def test_origin_maps_to_origin(self):
        result = map_to_screen(Point2D(0, 0), (640, 480), (1920, 1080))
        assert result == (0, 0)

    def test_far_corner_maps_to_far_corner(self):
        result = map_to_screen(Point2D(640, 480), (640, 480), (1920, 1080))
        assert result == (1920, 1080)

    def test_center_maps_to_center(self):
        result = map_to_screen(Point2D(320, 240), (640, 480), (1920, 1080))
        assert result == (960, 540)

    def test_clips_negative_coordinates(self):
        """A point outside the frame to the left/top should clip to (0, 0)."""
        result = map_to_screen(Point2D(-100, -50), (640, 480), (1920, 1080))
        assert result == (0, 0)

    def test_clips_coordinates_past_frame(self):
        """A point past the frame's edge should clip to the screen edge."""
        result = map_to_screen(Point2D(700, 500), (640, 480), (1920, 1080))
        assert result == (1920, 1080)

    def test_zero_frame_size_safe(self):
        """A degenerate frame size returns (0, 0) instead of dividing by zero."""
        result = map_to_screen(Point2D(0, 0), (0, 0), (1920, 1080))
        assert result == (0, 0)


class TestSmooth:
    def test_returns_new_when_no_previous(self):
        assert smooth(None, (100, 200), 0.3) == (100, 200)

    def test_returns_previous_when_factor_zero(self):
        assert smooth((10, 20), (100, 200), 0.0) == (10, 20)

    def test_returns_new_when_factor_one(self):
        assert smooth((10, 20), (100, 200), 1.0) == (100, 200)

    def test_clamps_negative_factor(self):
        """Negative factor is treated as 0 — never extrapolate backwards."""
        assert smooth((10, 20), (100, 200), -0.5) == (10, 20)

    def test_clamps_factor_above_one(self):
        assert smooth((10, 20), (100, 200), 1.5) == (100, 200)

    def test_partial_smoothing(self):
        """Factor 0.5 should produce the exact midpoint."""
        assert smooth((0, 0), (100, 200), 0.5) == (50, 100)

    @pytest.mark.parametrize(
        "prev,new,factor,expected",
        [
            ((0, 0), (10, 0), 0.1, (1, 0)),
            ((0, 0), (10, 0), 0.9, (9, 0)),
            ((100, 100), (200, 200), 0.25, (125, 125)),
        ],
    )
    def test_known_values(self, prev, new, factor, expected):
        assert smooth(prev, new, factor) == expected
