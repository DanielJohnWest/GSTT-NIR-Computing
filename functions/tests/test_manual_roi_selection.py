from functions.relaxometry.manual_roi_selection import manual_roi_selection
import numpy as np
import matplotlib.pyplot as plt

def test_manual_roi_selection():
    # Create a synthetic image
    img = np.zeros((100, 100), dtype=np.uint8)

    # Simulate user input for ROI selection
    # Here we simulate clicking the center and edge of 9 ROIs
    centers = [(30, 30), (70, 30), (30, 70), (70, 70), (50, 50), (20, 50), (80, 50), (50, 20), (50, 80)]
    radii = [8] * 9

    # Mock plt.ginput to return the simulated coordinates
    original_ginput = plt.ginput
    plt.ginput = lambda n, timeout=-1: [(c[0], c[1]) for c in centers[:n]] + [(c[0] + r, c[1]) for c, r in zip(centers[:n], radii[:n])]

    try:
        selected_centers, selected_radii = manual_roi_selection(img)
        assert len(selected_centers) == len(selected_radii) == 9
        for i in range(9):
            assert np.isclose(selected_centers[i][0], centers[i][0])
            assert np.isclose(selected_centers[i][1], centers[i][1])
            assert np.isclose(selected_radii[i], radii[i])
    finally:
        plt.ginput = original_ginput