"""The per-frame engine.

Combines: HandTracker → detector → state machine → mouse controller.
Designed to be testable: `process_frame` is a pure function on inputs,
so tests can drive the engine with synthetic frames and a recording mouse.
"""

from __future__ import annotations

from app.controllers.mouse import MouseController
from app.core.config import Config
from app.gestures.detector import GestureReading, detect_gesture
from app.gestures.state_machine import ActionType, GestureStateMachine
from app.tracking.geometry import map_to_screen, smooth
from app.tracking.hand_tracker import HandLandmarks


class VirtualMouseEngine:
    """Glues tracking → gestures → mouse actions for one webcam stream."""

    def __init__(self, config: Config, mouse: MouseController):
        self.config = config
        self.mouse = mouse
        self._screen_size = mouse.screen_size()
        self._state_machine = GestureStateMachine(
            click_cooldown_seconds=config.click_cooldown_seconds,
        )
        self._last_cursor: tuple[int, int] | None = None

    def process_landmarks(
        self,
        landmarks: HandLandmarks,
        *,
        frame_size: tuple[int, int],
        now_seconds: float,
    ) -> tuple[GestureReading, ActionType]:
        """Process a single frame's landmarks. Drives the mouse as a side effect.

        Returns (reading, action_type) so the caller can render an HUD.
        """
        _frame_w, frame_h = frame_size

        # 1. Gesture detection.
        reading = detect_gesture(
            landmarks,
            frame_height=frame_h,
            click_threshold_px=self.config.click_threshold_px,
            right_click_threshold_px=self.config.right_click_threshold_px,
            scroll_zone_top_px=self.config.scroll_zone_top_px,
            scroll_zone_bottom_offset_px=self.config.scroll_zone_bottom_offset_px,
        )

        # 2. State machine decides what to actually do this frame.
        action = self._state_machine.step(reading, now_seconds)

        # 3. Apply the action.
        if action.type == ActionType.MOVE:
            screen_x, screen_y = map_to_screen(
                landmarks.index_finger_tip,
                frame_size=frame_size,
                screen_size=self._screen_size,
            )
            smoothed = smooth(self._last_cursor, (screen_x, screen_y), self.config.smoothing_factor)
            self.mouse.move(*smoothed)
            self._last_cursor = smoothed

        elif action.type == ActionType.CLICK:
            self.mouse.click()

        elif action.type == ActionType.RIGHT_CLICK:
            self.mouse.right_click()

        elif action.type == ActionType.SCROLL_UP:
            self.mouse.scroll(self.config.scroll_step)

        elif action.type == ActionType.SCROLL_DOWN:
            self.mouse.scroll(-self.config.scroll_step)

        return reading, action.type
