"""Hand-tracking abstraction over MediaPipe.

We wrap MediaPipe behind a small dataclass interface so the rest of the
code never touches MediaPipe directly. Two payoffs:

  * Tests can construct fake `HandLandmarks` instances without needing
    a real camera, MediaPipe, or even OpenCV.
  * Swapping MediaPipe for another tracker (MediaPipe Tasks, or a custom
    model) only changes this file.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.tracking.geometry import Point2D

# MediaPipe landmark indices — named here so the rest of the code never
# uses magic numbers. Source: MediaPipe Hands documentation.
LANDMARK_WRIST = 0
LANDMARK_THUMB_TIP = 4
LANDMARK_INDEX_FINGER_TIP = 8
LANDMARK_MIDDLE_FINGER_TIP = 12
LANDMARK_RING_FINGER_TIP = 16
LANDMARK_PINKY_TIP = 20


@dataclass(frozen=True)
class HandLandmarks:
    """A minimal hand-pose snapshot in *pixel* coordinates for one frame.

    Only the four landmarks we actually use are surfaced. If we ever need
    more (e.g. finger PIPs for finer gestures), add them here and update
    `from_mediapipe`.
    """

    wrist: Point2D
    thumb_tip: Point2D
    index_finger_tip: Point2D
    middle_finger_tip: Point2D

    @classmethod
    def from_mediapipe(cls, landmarks, frame_width: int, frame_height: int) -> HandLandmarks:
        """Convert a MediaPipe hand_landmarks result to our shape.

        MediaPipe returns normalized [0, 1] coords; we scale to pixels here
        so downstream code can stay in one coordinate system.
        """

        def to_pixel(idx: int) -> Point2D:
            lm = landmarks.landmark[idx]
            return Point2D(x=lm.x * frame_width, y=lm.y * frame_height)

        return cls(
            wrist=to_pixel(LANDMARK_WRIST),
            thumb_tip=to_pixel(LANDMARK_THUMB_TIP),
            index_finger_tip=to_pixel(LANDMARK_INDEX_FINGER_TIP),
            middle_finger_tip=to_pixel(LANDMARK_MIDDLE_FINGER_TIP),
        )


class HandTracker:
    """Thin wrapper over `mediapipe.solutions.hands.Hands`.

    Lazy-imports MediaPipe so unit tests can import this module without
    needing the dependency installed.
    """

    def __init__(
        self,
        *,
        max_hands: int = 1,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
    ):
        # Lazy import — keeps test imports cheap.
        import mediapipe as mp

        self._mp_hands = mp.solutions.hands
        self._mp_drawing = mp.solutions.drawing_utils
        self._hands = self._mp_hands.Hands(
            max_num_hands=max_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def process(self, rgb_frame) -> object:
        """Run hand detection on a single RGB frame. Returns MediaPipe result."""
        return self._hands.process(rgb_frame)

    def draw_landmarks(self, frame, hand_landmarks) -> None:
        """Render the hand skeleton onto a BGR frame (in-place)."""
        self._mp_drawing.draw_landmarks(frame, hand_landmarks, self._mp_hands.HAND_CONNECTIONS)

    def close(self) -> None:
        self._hands.close()
