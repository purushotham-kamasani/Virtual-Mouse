"""Pure geometry helpers.

Kept dependency-free (just math) so the tests can run with no webcam,
no MediaPipe, no display.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Point2D:
    """A 2D point in some coordinate space (pixels, normalized, etc.)."""

    x: float
    y: float


def euclidean_distance(a: Point2D, b: Point2D) -> float:
    """Standard Euclidean distance between two 2D points."""
    return math.hypot(b.x - a.x, b.y - a.y)


def map_to_screen(
    point: Point2D,
    frame_size: tuple[int, int],
    screen_size: tuple[int, int],
) -> tuple[int, int]:
    """Map a point in webcam-frame space to physical-screen coordinates.

    Clips to the frame first so a noisy detection outside the frame doesn't
    push the cursor past the edges of the screen.
    """
    frame_w, frame_h = frame_size
    screen_w, screen_h = screen_size

    clipped_x = max(0, min(point.x, frame_w))
    clipped_y = max(0, min(point.y, frame_h))

    # Linear interpolation from [0, frame_dim] → [0, screen_dim].
    if frame_w <= 0 or frame_h <= 0:
        return (0, 0)

    screen_x = (clipped_x / frame_w) * screen_w
    screen_y = (clipped_y / frame_h) * screen_h
    return int(screen_x), int(screen_y)


def smooth(prev: tuple[int, int] | None, new: tuple[int, int], factor: float) -> tuple[int, int]:
    """Exponential smoothing — reduces jitter from frame-to-frame tracking noise.

    `factor` is the weight of the *new* sample (0 = always old, 1 = always new).
    """
    if prev is None:
        return new
    if factor <= 0:
        return prev
    if factor >= 1:
        return new
    smoothed_x = int(prev[0] + (new[0] - prev[0]) * factor)
    smoothed_y = int(prev[1] + (new[1] - prev[1]) * factor)
    return smoothed_x, smoothed_y
