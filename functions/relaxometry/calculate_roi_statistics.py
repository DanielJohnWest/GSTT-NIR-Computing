import numpy as np


def calculate_roi_statistics(tmap, centers, radii):

    roi_means = []
    roi_stds = []

    height, width = tmap.shape

    for center, radius in zip(centers, radii):

        x0, y0 = center

        # Create coordinate grids
        y, x = np.ogrid[:height, :width]

        # Circular mask
        mask = (x - x0)**2 + (y - y0)**2 <= radius**2

        # Extract pixels inside ROI
        roi_pixels = tmap[mask]

        # Remove invalid pixels if required
        roi_pixels = roi_pixels[np.isfinite(roi_pixels)]

        # Calculate statistics
        mean_value = np.mean(roi_pixels)
        std_value = np.std(roi_pixels)

        roi_means.append(mean_value)
        roi_stds.append(std_value)

    return roi_means, roi_stds