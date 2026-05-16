"""Gesture detection — pure logic over hand landmarks.

This module decides what gesture is *currently being shown*. It does NOT
decide whether to act on it (that's the job of GestureStateMachine, which
handles debouncing).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from app.tracking.geometry import euclidean_distance
from app.tracking.hand_tracker import HandLandmarks


class GestureType(str, enum.Enum):
    """Discrete gesture states detectable from a single frame."""

    NONE = "none"
    MOVE = "move"
    LEFT_CLICK = "left_click"  # thumb tip touches index tip
    RIGHT_CLICK = "right_click"  # index tip touches middle tip
    SCROLL_UP = "scroll_up"  # wrist near top of frame
    SCROLL_DOWN = "scroll_down"  # wrist near bottom of frame


@dataclass(frozen=True)
class GestureReading:
    """One frame's worth of gesture state plus the measurements behind it."""

    gesture: GestureType
    index_thumb_distance: float
    index_middle_distance: float
    wrist_y: float


def detect_gesture(
    landmarks: HandLandmarks,
    *,
    frame_height: int,
    click_threshold_px: float,
    right_click_threshold_px: float,
    scroll_zone_top_px: float,
    scroll_zone_bottom_offset_px: float,
) -> GestureReading:
    """Classify what gesture (if any) the hand is currently showing.

    Detection priority (a single frame can only have one gesture):
      1. Left click  — thumb pinching index
      2. Right click — index pinching middle
      3. Scroll      — wrist parked at top/bottom of the frame
      4. Move        — default; cursor follows the index finger
    """
    d_it = euclidean_distance(landmarks.index_finger_tip, landmarks.thumb_tip)
    d_im = euclidean_distance(landmarks.index_finger_tip, landmarks.middle_finger_tip)
    wrist_y = landmarks.wrist.y

    if d_it <= click_threshold_px:
        gesture = GestureType.LEFT_CLICK
    elif d_im <= right_click_threshold_px:
        gesture = GestureType.RIGHT_CLICK
    elif wrist_y <= scroll_zone_top_px:
        gesture = GestureType.SCROLL_UP
    elif wrist_y >= frame_height - scroll_zone_bottom_offset_px:
        gesture = GestureType.SCROLL_DOWN
    else:
        gesture = GestureType.MOVE

    return GestureReading(
        gesture=gesture,
        index_thumb_distance=d_it,
        index_middle_distance=d_im,
        wrist_y=wrist_y,
    )
