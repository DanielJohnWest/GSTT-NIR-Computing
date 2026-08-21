from functions.relaxometry.find_rois import find_rois
import cv2
import numpy as np

def test_find_rois():
    # Create a synthetic image with circles
    img = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(img, (30, 30), 8, 255, -1)  # Circle 1
    cv2.circle(img, (70, 30), 8, 255, -1)  # Circle 2
    cv2.circle(img, (30, 70), 8, 255, -1)  # Circle 3
    cv2.circle(img, (70, 70), 8, 255, -1)  # Circle 4
    cv2.circle(img, (50, 50), 8, 255, -1)  # Circle 5
    cv2.circle(img, (20, 50), 8, 255, -1)  # Circle 6
    cv2.circle(img, (80, 50), 8, 255, -1)  # Circle 7
    cv2.circle(img, (50, 20), 8, 255, -1)  # Circle 8
    cv2.circle(img, (50, 80), 8, 255, -1)  # Circle 9

    centers, radii, status = find_rois(img.astype(np.float32), task=1)

    assert status == 1
    assert len(centers) == len(radii) == 9