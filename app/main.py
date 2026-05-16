"""CLI entry point.

This is the one module that's *not* easily testable (real webcam, real
GUI window) — and that's fine. We keep it small and let the engine + state
machine carry the testable weight.

Run with:
    python -m app.main
    virtual-mouse           # installed via console_scripts in pyproject.toml
    virtual-mouse --calibrate
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque

from app.controllers.mouse import PyAutoGUIMouse
from app.core import Config, configure_logging, get_logger
from app.engine import VirtualMouseEngine
from app.tracking.hand_tracker import HandLandmarks, HandTracker

_logger = get_logger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="virtual-mouse",
        description="Hands-free mouse control via webcam (MediaPipe + PyAutoGUI).",
    )
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default: 0)")
    parser.add_argument(
        "--click-threshold",
        type=int,
        default=None,
        help="Pinch-to-click pixel distance threshold (default: 30)",
    )
    parser.add_argument(
        "--smoothing",
        type=float,
        default=None,
        help="Cursor smoothing factor 0..1 (default: 0.3)",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Run a 10-second calibration to suggest threshold values for your setup",
    )
    parser.add_argument(
        "--no-window",
        action="store_true",
        help="Run headless (don't open the OpenCV preview window)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = parse_args(argv)

    config = Config.from_env()
    overrides: dict[str, object] = {"camera_index": args.camera}
    if args.click_threshold is not None:
        overrides["click_threshold_px"] = args.click_threshold
    if args.smoothing is not None:
        overrides["smoothing_factor"] = args.smoothing
    config = config.with_overrides(**overrides)

    if args.calibrate:
        return run_calibration(config)
    return run_main_loop(config, show_window=not args.no_window)


def run_main_loop(config: Config, *, show_window: bool) -> int:
    """The main interaction loop. Imports cv2 lazily so unit tests don't need it."""
    import cv2

    mouse = PyAutoGUIMouse()
    tracker = HandTracker(
        max_hands=config.max_hands,
        min_detection_confidence=config.min_detection_confidence,
        min_tracking_confidence=config.min_tracking_confidence,
    )
    engine = VirtualMouseEngine(config, mouse)

    cap = cv2.VideoCapture(config.camera_index)
    if not cap.isOpened():
        _logger.error("camera_open_failed", extra={"index": config.camera_index})
        print(
            f"\nError: Could not open webcam at index {config.camera_index}.\n"
            "  - On macOS, grant camera access to Terminal in System Settings → Privacy & Security.\n"
            "  - Try --camera 1 if you have multiple cameras.\n",
            file=sys.stderr,
        )
        return 1

    _logger.info("started")
    print("\nVirtual Mouse — running. Press 'q' in the preview window to quit.\n")

    fps_window: deque[float] = deque(maxlen=30)
    last_frame_time = time.monotonic()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                _logger.warning("frame_read_failed")
                break

            # Mirror so the cursor moves in the natural direction.
            frame = cv2.flip(frame, 1)
            frame_h, frame_w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            result = tracker.process(rgb_frame)

            now = time.monotonic()
            reading_str = ""
            action_str = "—"

            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    if config.show_landmarks:
                        tracker.draw_landmarks(frame, hand_landmarks)

                    landmarks = HandLandmarks.from_mediapipe(hand_landmarks, frame_w, frame_h)
                    reading, action = engine.process_landmarks(
                        landmarks, frame_size=(frame_w, frame_h), now_seconds=now
                    )
                    reading_str = (
                        f"d(i-t)={reading.index_thumb_distance:.0f}  "
                        f"d(i-m)={reading.index_middle_distance:.0f}"
                    )
                    action_str = action.value

            # FPS overlay.
            dt = now - last_frame_time
            last_frame_time = now
            if dt > 0:
                fps_window.append(1.0 / dt)
            avg_fps = sum(fps_window) / len(fps_window) if fps_window else 0.0

            if show_window:
                if config.show_fps_overlay:
                    cv2.putText(
                        frame,
                        f"FPS: {avg_fps:5.1f}   action: {action_str}   {reading_str}",
                        (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (21, 97, 102),  # teal-ish
                        2,
                        cv2.LINE_AA,
                    )
                cv2.imshow(config.window_title, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        cap.release()
        if show_window:
            cv2.destroyAllWindows()
        tracker.close()
        _logger.info("stopped")

    return 0


def run_calibration(config: Config) -> int:
    """10-second calibration to suggest click_threshold_px.

    Asks the user to make a relaxed open hand, then a pinch, and reports
    distances. From these we recommend a threshold.
    """
    import cv2

    tracker = HandTracker(
        max_hands=config.max_hands,
        min_detection_confidence=config.min_detection_confidence,
    )
    cap = cv2.VideoCapture(config.camera_index)
    if not cap.isOpened():
        print(f"Error: Could not open webcam at index {config.camera_index}.", file=sys.stderr)
        return 1

    samples_open: list[float] = []
    samples_pinch: list[float] = []
    phases = [("OPEN hand wide", samples_open, 5.0), ("PINCH thumb to index", samples_pinch, 5.0)]

    try:
        for label, sink, duration in phases:
            print(f"\n=== {label} for {duration:.0f}s ===")
            start = time.monotonic()
            while time.monotonic() - start < duration:
                ok, frame = cap.read()
                if not ok:
                    break
                frame = cv2.flip(frame, 1)
                frame_h, frame_w, _ = frame.shape
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = tracker.process(rgb)
                if result.multi_hand_landmarks:
                    for hl in result.multi_hand_landmarks:
                        landmarks = HandLandmarks.from_mediapipe(hl, frame_w, frame_h)
                        from app.tracking.geometry import euclidean_distance

                        sink.append(
                            euclidean_distance(landmarks.index_finger_tip, landmarks.thumb_tip)
                        )
                        tracker.draw_landmarks(frame, hl)
                cv2.putText(
                    frame,
                    label,
                    (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (21, 97, 102),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow("Calibration", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    return 1
    finally:
        cap.release()
        cv2.destroyAllWindows()
        tracker.close()

    if not samples_open or not samples_pinch:
        print("\nCalibration failed: no hand detected. Try again with better lighting.")
        return 1

    open_min = min(samples_open)
    pinch_max = max(samples_pinch)
    # Pick midpoint between the largest pinch and smallest open — gives a stable threshold.
    suggested = int((open_min + pinch_max) / 2)
    print(
        f"\nResults:"
        f"\n  open-hand min distance:  {open_min:.0f}px"
        f"\n  pinch max distance:      {pinch_max:.0f}px"
        f"\n  suggested click threshold: {suggested}px"
        f"\n\nTo apply, run:"
        f"\n  virtual-mouse --click-threshold {suggested}"
        f"\nor set the env var:  export VM_CLICK_THRESHOLD_PX={suggested}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
