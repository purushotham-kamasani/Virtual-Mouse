"""Gesture state machine — turns per-frame readings into discrete actions.

This is the most subtle part of the whole project. Without it, holding a
pinch for half a second would fire 15 clicks (one per webcam frame at 30fps).
The state machine collapses sustained gestures into single events.

It exposes a tiny `step()` method that takes a reading + the current
monotonic time and returns the *Action* to perform this frame (or None).

Tests for this module run with no MediaPipe, no OpenCV, no display — they
just feed in synthetic readings and assert on the resulting actions.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from app.gestures.detector import GestureReading, GestureType


class ActionType(str, enum.Enum):
    """What the controllers layer should do this frame."""

    NONE = "none"
    MOVE = "move"
    CLICK = "click"
    RIGHT_CLICK = "right_click"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"


@dataclass(frozen=True)
class Action:
    type: ActionType


class GestureStateMachine:
    """Edge-triggered debouncer.

    A click only fires on the *transition* from non-click to click — and
    even then, only if `click_cooldown_seconds` has passed since the last
    click. Holding a pinch for 5 seconds = exactly one click, not 150.

    Scrolling is also rate-limited, but with a shorter cooldown since
    repeated scrolls are usually intentional.
    """

    def __init__(
        self, *, click_cooldown_seconds: float = 0.3, scroll_cooldown_seconds: float = 0.1
    ):
        self._click_cooldown = click_cooldown_seconds
        self._scroll_cooldown = scroll_cooldown_seconds
        self._prev_gesture: GestureType = GestureType.NONE
        self._last_click_at: float = -1e9
        self._last_right_click_at: float = -1e9
        self._last_scroll_at: float = -1e9

    def step(self, reading: GestureReading, now_seconds: float) -> Action:
        """Compute the action for this frame and update internal state."""
        gesture = reading.gesture
        action = self._decide(gesture, now_seconds)
        self._prev_gesture = gesture
        return action

    def _decide(self, gesture: GestureType, now: float) -> Action:
        # Click: fire only on transition into LEFT_CLICK, with cooldown.
        if gesture == GestureType.LEFT_CLICK:
            if (
                self._prev_gesture != GestureType.LEFT_CLICK
                and now - self._last_click_at >= self._click_cooldown
            ):
                self._last_click_at = now
                return Action(ActionType.CLICK)
            # Still pinching — suppress further clicks. Don't move the cursor
            # while pinching either, since users tend to drift mid-click.
            return Action(ActionType.NONE)

        if gesture == GestureType.RIGHT_CLICK:
            if (
                self._prev_gesture != GestureType.RIGHT_CLICK
                and now - self._last_right_click_at >= self._click_cooldown
            ):
                self._last_right_click_at = now
                return Action(ActionType.RIGHT_CLICK)
            return Action(ActionType.NONE)

        if gesture in (GestureType.SCROLL_UP, GestureType.SCROLL_DOWN):
            if now - self._last_scroll_at < self._scroll_cooldown:
                return Action(ActionType.NONE)
            self._last_scroll_at = now
            return Action(
                ActionType.SCROLL_UP if gesture == GestureType.SCROLL_UP else ActionType.SCROLL_DOWN
            )

        if gesture == GestureType.MOVE:
            return Action(ActionType.MOVE)

        return Action(ActionType.NONE)
