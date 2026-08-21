import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle


def manual_roi_selection(img1, n_rois=9):
    """
    Manually select circular ROIs.

    Parameters
    ----------
    img1 : ndarray
        Image on which to select ROIs.
    n_rois : int, optional
        Number of ROIs to select (default = 9).

    Returns
    -------
    centers : ndarray
        Array of ROI centres.
    radii : ndarray
        Array of ROI radii.
    """

    while True:

        print(
            "Click the centre and then the edge of each ROI "
            "(left to right, top to bottom)"
        )

        centers = []
        radii = []

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(img1, cmap="gray")
        ax.axis("off")

        for i in range(n_rois):

            ax.set_title(
                f"ROI {i+1}/{n_rois}\n"
                "Click the centre then the edge"
            )
            plt.draw()

            coords = plt.ginput(2, timeout=-1)

            if len(coords) != 2:
                plt.close(fig)
                raise RuntimeError("ROI selection cancelled.")

            xc, yc = coords[0]
            xe, ye = coords[1]

            radius = np.hypot(xe - xc, ye - yc)

            centers.append((xc, yc))
            radii.append(radius)

            # Draw circle
            circle = Circle(
                (xc, yc),
                radius,
                edgecolor="red",
                facecolor="none",
                linewidth=2,
            )

            ax.add_patch(circle)

            # Draw centre
            ax.plot(xc, yc, "r+", markersize=10)

            # Draw ROI number
            ax.text(
                xc,
                yc,
                str(i + 1),
                color="yellow",
                fontsize=12,
                ha="center",
                va="center",
                weight="bold",
            )

            plt.draw()

        ax.set_title("Review ROIs")
        plt.draw()

        answer = input(
            "Accept these ROIs? (y = yes, n = repeat): "
        ).strip().lower()

        plt.close(fig)

        if answer == "y":
            return np.asarray(centers), np.asarray(radii)

        print("Repeating ROI selection...\n")