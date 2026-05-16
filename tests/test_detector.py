"""Tests for gesture detection logic."""

from __future__ import annotations

from app.gestures.detector import GestureType, detect_gesture
from tests.conftest import make_landmarks

THRESHOLDS = dict(
    frame_height=480,
    click_threshold_px=30,
    right_click_threshold_px=30,
    scroll_zone_top_px=50,
    scroll_zone_bottom_offset_px=50,
)


class TestLeftClick:
    def test_click_when_thumb_and_index_pinch(self):
        landmarks = make_landmarks(
            index_xy=(100, 100),
            thumb_xy=(110, 105),  # very close — pinch
            middle_xy=(200, 200),
        )
        reading = detect_gesture(landmarks, **THRESHOLDS)
        assert reading.gesture == GestureType.LEFT_CLICK

    def test_no_click_just_above_threshold(self):
        landmarks = make_landmarks(
            index_xy=(100, 100),
            thumb_xy=(135, 100),  # 35px apart, threshold is 30
            middle_xy=(200, 200),
        )
        reading = detect_gesture(landmarks, **THRESHOLDS)
        assert reading.gesture != GestureType.LEFT_CLICK


class TestRightClick:
    def test_right_click_when_index_and_middle_pinch(self):
        landmarks = make_landmarks(
            index_xy=(100, 100),
            thumb_xy=(300, 100),
            middle_xy=(110, 105),  # close to index
        )
        reading = detect_gesture(landmarks, **THRESHOLDS)
        assert reading.gesture == GestureType.RIGHT_CLICK

    def test_left_click_wins_over_right_when_both_satisfied(self):
        """If both thumb-index AND index-middle are close, left click takes priority.

        Without this priority a user pinching all three fingers would get
        ambiguous behavior.
        """
        landmarks = make_landmarks(
            index_xy=(100, 100),
            thumb_xy=(105, 100),  # close
            middle_xy=(110, 100),  # also close
        )
        reading = detect_gesture(landmarks, **THRESHOLDS)
        assert reading.gesture == GestureType.LEFT_CLICK


class TestScroll:
    def test_scroll_up_when_wrist_at_top(self):
        landmarks = make_landmarks(
            index_xy=(300, 200),
            thumb_xy=(400, 200),
            middle_xy=(500, 200),
            wrist_xy=(300, 30),  # above the 50px scroll zone
        )
        reading = detect_gesture(landmarks, **THRESHOLDS)
        assert reading.gesture == GestureType.SCROLL_UP

    def test_scroll_down_when_wrist_at_bottom(self):
        landmarks = make_landmarks(
            index_xy=(300, 200),
            thumb_xy=(400, 200),
            middle_xy=(500, 200),
            wrist_xy=(300, 450),  # below frame_height - 50 = 430
        )
        reading = detect_gesture(landmarks, **THRESHOLDS)
        assert reading.gesture == GestureType.SCROLL_DOWN

    def test_no_scroll_when_wrist_in_middle(self):
        landmarks = make_landmarks(
            index_xy=(300, 200),
            thumb_xy=(400, 200),
            middle_xy=(500, 200),
            wrist_xy=(300, 240),
        )
        reading = detect_gesture(landmarks, **THRESHOLDS)
        assert reading.gesture == GestureType.MOVE

    def test_click_beats_scroll_when_both_active(self):
        """If the user happens to pinch with the wrist in a scroll zone,
        the click should still register."""
        landmarks = make_landmarks(
            index_xy=(300, 30),
            thumb_xy=(305, 30),  # pinch
            middle_xy=(500, 30),
            wrist_xy=(300, 30),  # in scroll zone
        )
        reading = detect_gesture(landmarks, **THRESHOLDS)
        assert reading.gesture == GestureType.LEFT_CLICK


class TestMove:
    def test_move_is_default(self):
        landmarks = make_landmarks(
            index_xy=(300, 240),
            thumb_xy=(400, 240),
            middle_xy=(500, 240),
            wrist_xy=(300, 240),
        )
        reading = detect_gesture(landmarks, **THRESHOLDS)
        assert reading.gesture == GestureType.MOVE


def test_reading_contains_measurements():
    """The GestureReading should expose the underlying distances for HUD/debug."""
    landmarks = make_landmarks(
        index_xy=(0, 0),
        thumb_xy=(3, 4),  # distance 5
        middle_xy=(0, 10),  # distance 10
        wrist_xy=(0, 240),
    )
    reading = detect_gesture(landmarks, **THRESHOLDS)
    assert reading.index_thumb_distance == 5.0
    assert reading.index_middle_distance == 10.0
    assert reading.wrist_y == 240
