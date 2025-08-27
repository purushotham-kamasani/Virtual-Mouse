import math
import pytest
from exampple import calculate_distance, map_coordinates, detect_gestures

# Test calculate_distance
def test_calculate_distance():
    """Test distance calculation between two points."""
    print("Testing calculate_distance...")
    # Standard cases
    assert calculate_distance(0, 0, 3, 4) == 5  # Pythagorean triplet
    assert calculate_distance(0, 0, 0, 0) == 0
    assert calculate_distance(-3, -4, 3, 4) == pytest.approx(10.0)
    # Floating-point precision
    assert calculate_distance(1.5, 2.5, 4.5, 6.5) == pytest.approx(5.0)
    print("test_calculate_distance passed!")

# Test map_coordinates
def test_map_coordinates():
    """Test mapping of coordinates from frame to screen dimensions."""
    print("Testing map_coordinates...")
    screen_width, screen_height = 1920, 1080
    frame_width, frame_height = 640, 480

    # Standard cases
    assert map_coordinates(320, 240, frame_width, frame_height, screen_width, screen_height) == (960, 540)
    assert map_coordinates(0, 0, frame_width, frame_height, screen_width, screen_height) == (0, 0)
    assert map_coordinates(640, 480, frame_width, frame_height, screen_width, screen_height) == (1920, 1080)

    # Edge cases
    assert map_coordinates(800, 600, frame_width, frame_height, screen_width, screen_height) == (1920, 1080)
    assert map_coordinates(-100, -100, frame_width, frame_height, screen_width, screen_height) == (0, 0)
    print("test_map_coordinates passed!")

# Test detect_gestures
def test_detect_gestures():
    """Test detection of gestures based on distances."""
    print("Testing detect_gestures...")
    index_finger_tip = (100, 100)
    thumb_tip = (120, 120)  # Distance ~28.28
    middle_finger_tip = (200, 200)  # Distance ~141.42

    # Standard cases
    gestures = detect_gestures(index_finger_tip, thumb_tip, middle_finger_tip, distance_threshold=30)
    assert gestures['click'] is True
    assert gestures['right_click'] is False

    # Edge cases
    gestures = detect_gestures(index_finger_tip, (130, 130), middle_finger_tip, distance_threshold=50)
    assert gestures['click'] is False
    assert gestures['right_click'] is False  # Adjusted threshold to avoid false positives

    gestures = detect_gestures(index_finger_tip, (150, 150), (115, 115), distance_threshold=75)
    assert gestures['click'] is True
    assert gestures['right_click'] is True
    print("test_detect_gestures passed!")

# Main block to run tests
if __name__ == "__main__":
    print("Running tests manually...")
    try:
        test_calculate_distance()
        test_map_coordinates()
        test_detect_gestures()
        print("All tests passed successfully!")
    except AssertionError as e:
        print("Test failed:", e)
