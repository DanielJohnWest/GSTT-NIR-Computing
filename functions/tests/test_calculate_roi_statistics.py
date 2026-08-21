import numpy as np
from functions.relaxometry.calculate_roi_statistics import calculate_roi_statistics

def test_calculate_roi_statistics():

    tmap = np.ones((100, 100))

    centers = [
        (20, 20),
        (40, 20),
        (60, 20),
        (20, 40),
        (40, 40),
        (60, 40),
        (20, 60),
        (40, 60),
        (60, 60)
    ]

    radii = [3] * 9

    means, stds = calculate_roi_statistics(
        tmap,
        centers,
        radii
    )

    assert len(means) == 9
    assert len(stds) == 9

    for mean in means:
        assert np.isclose(mean, 1.0)

    for std in stds:
        assert np.isclose(std, 0.0)