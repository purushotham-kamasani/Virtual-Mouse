"""End-to-end engine tests with a recording mouse.

These tests drive the *whole* engine (detector → state machine → mouse)
with synthetic landmark sequences and assert on the resulting mouse events.
No real webcam, no real cursor — just the recorded event log.
"""

from __future__ import annotations

import pytest

from app.controllers.mouse import RecordingMouse
from app.core.config import Config
from app.engine import VirtualMouseEngine
from app.gestures.state_machine import ActionType
from tests.conftest import make_landmarks

FRAME_SIZE = (640, 480)


@pytest.fixture
def engine(config: Config) -> tuple[VirtualMouseEngine, RecordingMouse]:
    mouse = RecordingMouse(screen_size=(1920, 1080))
    return VirtualMouseEngine(config, mouse), mouse


class TestEngineMove:
    def test_move_drives_cursor(self, engine):
        eng, mouse = engine
        landmarks = make_landmarks(
            index_xy=(320, 240),  # center of frame
            thumb_xy=(500, 240),
            middle_xy=(500, 300),
            wrist_xy=(320, 240),
        )
        _, action = eng.process_landmarks(landmarks, frame_size=FRAME_SIZE, now_seconds=0.0)
        assert action == ActionType.MOVE
        # One move event recorded.
        move_events = [e for e in mouse.events if e[0] == "move"]
        assert len(move_events) == 1
        # Center frame → center screen.
        x, y = move_events[0][1]
        assert 900 <= x <= 1020  # ~960
        assert 510 <= y <= 570  # ~540


class TestEngineClick:
    def test_pinch_produces_one_click(self, engine):
        eng, mouse = engine
        pinch = make_landmarks(
            index_xy=(300, 240),
            thumb_xy=(305, 240),  # 5px → well below the 30px threshold
            middle_xy=(500, 240),
            wrist_xy=(300, 240),
        )
        eng.process_landmarks(pinch, frame_size=FRAME_SIZE, now_seconds=0.0)
        click_events = [e for e in mouse.events if e[0] == "click"]
        assert len(click_events) == 1

    def test_held_pinch_clicks_only_once(self, engine):
        """The whole point of the state machine. 60 pinch frames = 1 click."""
        eng, mouse = engine
        pinch = make_landmarks(
            index_xy=(300, 240),
            thumb_xy=(305, 240),
            middle_xy=(500, 240),
            wrist_xy=(300, 240),
        )
        for i in range(60):
            eng.process_landmarks(pinch, frame_size=FRAME_SIZE, now_seconds=i / 30.0)
        click_events = [e for e in mouse.events if e[0] == "click"]
        assert len(click_events) == 1


class TestEngineRightClick:
    def test_right_click_recorded(self, engine):
        eng, mouse = engine
        landmarks = make_landmarks(
            index_xy=(300, 240),
            thumb_xy=(500, 240),
            middle_xy=(305, 240),  # close to index → right click
            wrist_xy=(300, 240),
        )
        eng.process_landmarks(landmarks, frame_size=FRAME_SIZE, now_seconds=0.0)
        rc_events = [e for e in mouse.events if e[0] == "right_click"]
        assert len(rc_events) == 1


class TestEngineScroll:
    def test_scroll_up(self, engine):
        eng, mouse = engine
        landmarks = make_landmarks(
            index_xy=(300, 30),
            thumb_xy=(500, 30),
            middle_xy=(500, 30),
            wrist_xy=(300, 30),  # in scroll-up zone
        )
        eng.process_landmarks(landmarks, frame_size=FRAME_SIZE, now_seconds=0.0)
        scrolls = [e for e in mouse.events if e[0] == "scroll"]
        assert len(scrolls) == 1
        assert scrolls[0][1] > 0  # positive scroll amount = up

    def test_scroll_down(self, engine):
        eng, mouse = engine
        landmarks = make_landmarks(
            index_xy=(300, 450),
            thumb_xy=(500, 450),
            middle_xy=(500, 450),
            wrist_xy=(300, 450),  # in scroll-down zone
        )
        eng.process_landmarks(landmarks, frame_size=FRAME_SIZE, now_seconds=0.0)
        scrolls = [e for e in mouse.events if e[0] == "scroll"]
        assert len(scrolls) == 1
        assert scrolls[0][1] < 0


class TestEngineSmoothing:
    def test_cursor_smoothed_between_frames(self, config):
        """With smoothing=0.5, the second cursor position should be halfway
        between the first frame's position and the new target."""
        cfg = config.with_overrides(smoothing_factor=0.5)
        mouse = RecordingMouse(screen_size=(1920, 1080))
        eng = VirtualMouseEngine(cfg, mouse)

        # Frame 1: index at left edge.
        eng.process_landmarks(
            make_landmarks(
                index_xy=(0, 240),
                thumb_xy=(300, 240),
                middle_xy=(300, 240),
                wrist_xy=(0, 240),
            ),
            frame_size=FRAME_SIZE,
            now_seconds=0.0,
        )
        first_move = mouse.events[0][1]
        assert first_move == (0, 540)  # no smoothing on first frame

        # Frame 2: index at right edge — should be midway.
        eng.process_landmarks(
            make_landmarks(
                index_xy=(640, 240),
                thumb_xy=(300, 240),
                middle_xy=(300, 240),
                wrist_xy=(640, 240),
            ),
            frame_size=FRAME_SIZE,
            now_seconds=0.033,
        )
        second_move = mouse.events[1][1]
        # Halfway between (0, 540) and (1920, 540) = (960, 540).
        assert second_move == (960, 540)


class TestEngineRealisticSequence:
    def test_full_interaction(self, engine):
        """Move → pinch → hold → release → move → right-click → scroll."""
        eng, mouse = engine

        move = make_landmarks(
            index_xy=(320, 240),
            thumb_xy=(500, 240),
            middle_xy=(500, 240),
            wrist_xy=(320, 240),
        )
        pinch = make_landmarks(
            index_xy=(320, 240),
            thumb_xy=(325, 240),
            middle_xy=(500, 240),
            wrist_xy=(320, 240),
        )
        right = make_landmarks(
            index_xy=(320, 240),
            thumb_xy=(500, 240),
            middle_xy=(325, 240),
            wrist_xy=(320, 240),
        )
        scroll = make_landmarks(
            index_xy=(320, 30),
            thumb_xy=(500, 30),
            middle_xy=(500, 30),
            wrist_xy=(320, 30),
        )

        eng.process_landmarks(move, frame_size=FRAME_SIZE, now_seconds=0.00)
        eng.process_landmarks(pinch, frame_size=FRAME_SIZE, now_seconds=0.05)
        eng.process_landmarks(pinch, frame_size=FRAME_SIZE, now_seconds=0.08)  # held
        eng.process_landmarks(pinch, frame_size=FRAME_SIZE, now_seconds=0.12)  # still held
        eng.process_landmarks(move, frame_size=FRAME_SIZE, now_seconds=0.40)  # released
        eng.process_landmarks(right, frame_size=FRAME_SIZE, now_seconds=0.45)
        eng.process_landmarks(scroll, frame_size=FRAME_SIZE, now_seconds=0.60)

        kinds = [e[0] for e in mouse.events]
        assert kinds.count("click") == 1  # one click despite 3 pinch frames
        assert kinds.count("right_click") == 1
        assert kinds.count("scroll") == 1
        assert kinds.count("move") == 2  # one before pinch, one after release
