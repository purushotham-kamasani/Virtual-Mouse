import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time

# Initialize Mediapipe Hands and Drawing utilities
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# Screen dimensions
screen_width, screen_height = pyautogui.size()

# Utility Functions
def calculate_distance(x1, y1, x2, y2):
    """Calculate Euclidean distance between two points."""
    distance = np.hypot(x2 - x1, y2 - y1)
    print(f"Distance between ({x1}, {y1}) and ({x2}, {y2}): {distance}")
    return distance

def map_coordinates(x, y, frame_width, frame_height, screen_width, screen_height):
    """Map webcam coordinates to screen coordinates with bounds checking."""
    x = min(max(x, 0), frame_width)  # Clip x to [0, frame_width]
    y = min(max(y, 0), frame_height)  # Clip y to [0, frame_height]
    screen_x = np.interp(x, (0, frame_width), (0, screen_width))
    screen_y = np.interp(y, (0, frame_height), (0, screen_height))
    return int(screen_x), int(screen_y)

def detect_gestures(index_finger_tip, thumb_tip, middle_finger_tip, distance_threshold=30):
    """Detect gestures based on distances between fingers."""
    gestures = {}

    # Calculate distances
    distance_index_thumb = calculate_distance(index_finger_tip[0], index_finger_tip[1],
                                              thumb_tip[0], thumb_tip[1])
    distance_index_middle = calculate_distance(index_finger_tip[0], index_finger_tip[1],
                                               middle_finger_tip[0], middle_finger_tip[1])

    print(f"Distance Index-Thumb: {distance_index_thumb}, Threshold: {distance_threshold}")
    print(f"Distance Index-Middle: {distance_index_middle}, Threshold: {distance_threshold}")

    # Compare distances with the threshold
    gestures['click'] = distance_index_thumb <= distance_threshold
    gestures['right_click'] = distance_index_middle <= distance_threshold
    return gestures


# Main Application
def virtual_mouse():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        exit()

    click_delay = 0.3  # Delay to prevent multiple clicks
    double_click_enabled = False

    with mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7) as hands:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame from webcam.")
                break

            frame = cv2.flip(frame, 1)
            frame_height, frame_width, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb_frame)

            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                    # Extract relevant landmarks
                    index_finger_tip = (
                        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].x * frame_width,
                        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y * frame_height,
                    )
                    thumb_tip = (
                        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].x * frame_width,
                        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y * frame_height,
                    )
                    middle_finger_tip = (
                        hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].x * frame_width,
                        hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y * frame_height,
                    )
                    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

                    # Map index finger coordinates to screen space
                    screen_x, screen_y = map_coordinates(index_finger_tip[0], index_finger_tip[1],
                                                          frame_width, frame_height,
                                                          screen_width, screen_height)
                    pyautogui.moveTo(screen_x, screen_y)

                    # Detect gestures
                    gestures = detect_gestures(index_finger_tip, thumb_tip, middle_finger_tip)

                    if gestures['click']:
                        pyautogui.click()
                        pyautogui.doubleClick() if double_click_enabled else pyautogui.click()
                        time.sleep(click_delay)

                    if gestures['right_click']:
                        pyautogui.rightClick()
                        time.sleep(click_delay)

                    # Scroll gestures (based on wrist position)
                    wrist_y = wrist.y * frame_height
                    if wrist_y > frame_height - 50:
                        pyautogui.scroll(-10)
                    elif wrist_y < 50:
                        pyautogui.scroll(10)

            cv2.imshow("Virtual Mouse", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    virtual_mouse()
