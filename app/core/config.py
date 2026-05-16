"""Application configuration.

Everything tunable lives here. Override via:
  * CLI flags (see app/main.py)
  * Environment variables (VM_* prefix)
  * A calibration session — values get suggested then saved

The defaults work for an average hand at ~50cm from the webcam on a 1080p
display, but anyone with a smaller hand or different camera setup will
benefit from running `virtual-mouse --calibrate` once.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # --- Camera ---
    camera_index: int = 0
    target_fps: int = 30  # informational; OpenCV negotiates with the device

    # --- Hand tracking ---
    max_hands: int = 1
    min_detection_confidence: float = 0.7
    min_tracking_confidence: float = 0.5

    # --- Gesture thresholds (in pixels at frame resolution) ---
    click_threshold_px: int = 30
    right_click_threshold_px: int = 30
    scroll_zone_top_px: int = 50
    scroll_zone_bottom_offset_px: int = 50

    # --- Click debouncing ---
    # Without this, a single sustained pinch would fire many clicks per second.
    click_cooldown_seconds: float = 0.3

    # --- Cursor smoothing ---
    # 0 = no smoothing (jitter), 1 = totally frozen. ~0.3 is the sweet spot.
    smoothing_factor: float = 0.3

    # --- Scroll behavior ---
    scroll_step: int = 10

    # --- UI ---
    show_landmarks: bool = True
    show_fps_overlay: bool = True
    window_title: str = "Virtual Mouse"

    @classmethod
    def from_env(cls) -> Config:
        """Build a Config, overriding any attribute set via env var (VM_*)."""
        overrides: dict[str, object] = {}
        for field in cls.__dataclass_fields__:
            env_key = "VM_" + field.upper()
            raw = os.environ.get(env_key)
            if raw is None:
                continue
            current = getattr(cls, field)
            try:
                if isinstance(current, bool):
                    overrides[field] = raw.lower() in ("1", "true", "yes", "on")
                elif isinstance(current, int):
                    overrides[field] = int(raw)
                elif isinstance(current, float):
                    overrides[field] = float(raw)
                else:
                    overrides[field] = raw
            except ValueError:
                # Skip silently — config errors shouldn't crash the app.
                pass
        return cls(**overrides)

    def with_overrides(self, **kwargs: object) -> Config:
        """Return a new Config with the given fields overridden."""
        from dataclasses import replace

        return replace(self, **kwargs)
