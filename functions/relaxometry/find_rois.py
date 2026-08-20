import cv2
import numpy as np
"""
Automatically detect circular ROIs.

Parameters
----------
img1 : ndarray
    First image in the series.
task : int
    Reconstruction task (1-4).

Returns
-------
centers : ndarray or None
    Array of circle centres (N x 2).
radii : ndarray or None
    Array of circle radii.
roi_mode : int
    1 = automatic ROI detection successful
    2 = manual ROI placement required
"""
def find_rois(img1, task):
 # Detection parameters
    if task == 1:
        radius_range = (8, 9)
        sensitivity = 0.985
        edge_threshold = 0.07

    elif task == 3:
        radius_range = (6, 11)
        sensitivity = 0.95
        edge_threshold = 0.10

    elif task in (2, 4):
        radius_range = (6, 13)
        sensitivity = 0.95
        edge_threshold = 0.10

    else:
        raise ValueError(f"Unknown task: {task}")

    # Convert image to uint8
    img = cv2.normalize(img1, None, 0, 255, cv2.NORM_MINMAX)
    img = img.astype(np.uint8)
    img = cv2.GaussianBlur(img, (5, 5), 0)

    # Detect circles
    circles = cv2.HoughCircles(
        img,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=20,
        param1=int(edge_threshold * 255),
        param2=(1 - sensitivity) * 100,
        minRadius=radius_range[0],
        maxRadius=radius_range[1],
    )

    # No circles detected
    if circles is None:
        print("No circles detected. Switching to manual ROI placement.")
        return None, None, 2

    circles = np.round(circles[0]).astype(int)

    # Wrong number of circles
    if len(circles) != 9:
        print(f"Detected {len(circles)} circles instead of 9.")
        print("Switching to manual ROI placement.")
        return None, None, 2

    # Success
    centers = circles[:, :2]
    radii = circles[:, 2]

    print("Automatic ROI detection successful.")

    return centers, radii, 1