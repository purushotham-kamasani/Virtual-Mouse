"""Shared pytest fixtures.

All tests run with NO webcam, NO MediaPipe, NO display. We construct
synthetic HandLandmarks directly and feed them to the engine + state machine.
"""

from __future__ import annotations

import pytest

from app.controllers.mouse import RecordingMouse
from app.core.config import Config
from app.tracking.geometry import Point2D
from app.tracking.hand_tracker import HandLandmarks


@pytest.fixture
def config() -> Config:
    """Default config — tests can `dataclasses.replace` for variations."""
    return Config()


@pytest.fixture
def recording_mouse() -> RecordingMouse:
    return RecordingMouse(screen_size=(1920, 1080))


def make_landmarks(
    *,
    index_xy: tuple[float, float],
    thumb_xy: tuple[float, float],
    middle_xy: tuple[float, float],
    wrist_xy: tuple[float, float] = (320.0, 240.0),
) -> HandLandmarks:
    """Construct a HandLandmarks with the four points we care about."""
    return HandLandmarks(
        wrist=Point2D(*wrist_xy),
        thumb_tip=Point2D(*thumb_xy),
        index_finger_tip=Point2D(*index_xy),
        middle_finger_tip=Point2D(*middle_xy),
    )
