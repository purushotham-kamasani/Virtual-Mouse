"""Tests for the gesture state machine — especially debouncing.

These are the most important tests in the project. The state machine is
what turns "60 frames of pinching per second" into "one click", and
getting it wrong means the cursor either flutters or clicks 30 times for
every intentional click. Critical correctness logic.
"""

from __future__ import annotations

from app.gestures.detector import GestureReading, GestureType
from app.gestures.state_machine import ActionType, GestureStateMachine


def _reading(gesture: GestureType) -> GestureReading:
    """Construct a minimal reading for tests that don't care about distances."""
    return GestureReading(
        gesture=gesture,
        index_thumb_distance=0.0,
        index_middle_distance=0.0,
        wrist_y=0.0,
    )


class TestClickDebouncing:
    def test_first_click_fires(self):
        sm = GestureStateMachine(click_cooldown_seconds=0.3)
        action = sm.step(_reading(GestureType.LEFT_CLICK), now_seconds=10.0)
        assert action.type == ActionType.CLICK

    def test_held_pinch_fires_only_once(self):
        """The headline scenario — user holds a pinch for many frames."""
        sm = GestureStateMachine(click_cooldown_seconds=0.3)

        # First frame: pinch starts → CLICK.
        assert sm.step(_reading(GestureType.LEFT_CLICK), 10.0).type == ActionType.CLICK

        # Next 60 frames @ 30fps: pinch continues → nothing.
        for i in range(1, 61):
            t = 10.0 + i / 30.0
            action = sm.step(_reading(GestureType.LEFT_CLICK), t)
            assert action.type == ActionType.NONE, f"Unexpected action at frame {i}: {action}"

    def test_release_then_re_pinch_fires_again(self):
        sm = GestureStateMachine(click_cooldown_seconds=0.3)

        # Pinch → click.
        assert sm.step(_reading(GestureType.LEFT_CLICK), 0.0).type == ActionType.CLICK
        # Release.
        sm.step(_reading(GestureType.MOVE), 0.5)
        # Pinch again → click (well past the cooldown).
        assert sm.step(_reading(GestureType.LEFT_CLICK), 1.0).type == ActionType.CLICK

    def test_cooldown_blocks_rapid_release_and_re_pinch(self):
        """Even if the user releases and re-pinches within the cooldown, no double-fire."""
        sm = GestureStateMachine(click_cooldown_seconds=0.3)
        assert sm.step(_reading(GestureType.LEFT_CLICK), 0.0).type == ActionType.CLICK
        sm.step(_reading(GestureType.MOVE), 0.05)
        # Cooldown is 0.3s; we re-pinch at t=0.1.
        assert sm.step(_reading(GestureType.LEFT_CLICK), 0.1).type == ActionType.NONE


class TestRightClickDebouncing:
    def test_right_click_fires_once(self):
        sm = GestureStateMachine()
        assert sm.step(_reading(GestureType.RIGHT_CLICK), 0.0).type == ActionType.RIGHT_CLICK
        # Sustained right-click → no more events.
        assert sm.step(_reading(GestureType.RIGHT_CLICK), 0.05).type == ActionType.NONE

    def test_right_click_independent_of_left_click_cooldown(self):
        """Doing left-click then right-click immediately should fire both."""
        sm = GestureStateMachine(click_cooldown_seconds=0.3)
        sm.step(_reading(GestureType.LEFT_CLICK), 0.0)
        # Different gesture type → not blocked.
        action = sm.step(_reading(GestureType.RIGHT_CLICK), 0.05)
        assert action.type == ActionType.RIGHT_CLICK


class TestMove:
    def test_move_fires_every_frame(self):
        """Move is a continuous action — every frame should produce a MOVE."""
        sm = GestureStateMachine()
        for t in (0.0, 0.033, 0.066, 0.1):
            assert sm.step(_reading(GestureType.MOVE), t).type == ActionType.MOVE

    def test_no_move_while_clicking(self):
        """While pinching, the cursor should freeze to prevent drift mid-click."""
        sm = GestureStateMachine()
        sm.step(_reading(GestureType.LEFT_CLICK), 0.0)
        action = sm.step(_reading(GestureType.LEFT_CLICK), 0.05)
        assert action.type == ActionType.NONE


class TestScrollRateLimit:
    def test_first_scroll_fires(self):
        sm = GestureStateMachine()
        action = sm.step(_reading(GestureType.SCROLL_UP), 0.0)
        assert action.type == ActionType.SCROLL_UP

    def test_scrolls_repeat_after_cooldown(self):
        sm = GestureStateMachine(scroll_cooldown_seconds=0.1)
        sm.step(_reading(GestureType.SCROLL_UP), 0.0)
        # 50ms later — still in cooldown.
        assert sm.step(_reading(GestureType.SCROLL_UP), 0.05).type == ActionType.NONE
        # 150ms later — fires again.
        assert sm.step(_reading(GestureType.SCROLL_UP), 0.15).type == ActionType.SCROLL_UP

    def test_scroll_direction_change_still_rate_limited(self):
        """Even switching direction shouldn't bypass the cooldown."""
        sm = GestureStateMachine(scroll_cooldown_seconds=0.1)
        sm.step(_reading(GestureType.SCROLL_UP), 0.0)
        assert sm.step(_reading(GestureType.SCROLL_DOWN), 0.05).type == ActionType.NONE


class TestRealisticSequence:
    def test_full_interaction(self):
        """Simulate: move → pinch → hold → release → move → right-click → release → scroll."""
        sm = GestureStateMachine(click_cooldown_seconds=0.3)

        # Move.
        assert sm.step(_reading(GestureType.MOVE), 0.0).type == ActionType.MOVE
        # Pinch.
        assert sm.step(_reading(GestureType.LEFT_CLICK), 0.05).type == ActionType.CLICK
        # Held.
        for t in (0.08, 0.1, 0.15):
            assert sm.step(_reading(GestureType.LEFT_CLICK), t).type == ActionType.NONE
        # Release + move.
        assert sm.step(_reading(GestureType.MOVE), 0.5).type == ActionType.MOVE
        # Right-click.
        assert sm.step(_reading(GestureType.RIGHT_CLICK), 0.55).type == ActionType.RIGHT_CLICK
        # Release.
        sm.step(_reading(GestureType.MOVE), 0.6)
        # Scroll up.
        assert sm.step(_reading(GestureType.SCROLL_UP), 0.7).type == ActionType.SCROLL_UP
