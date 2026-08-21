from functions.relaxometry.manual_roi_selection import manual_roi_selection
import numpy as np
import matplotlib.pyplot as plt

def test_manual_roi_selection_repeat(monkeypatch):

    img = np.zeros((100, 100), dtype=np.uint8)

    centers = [
        (30, 30),
        (70, 30),
        (30, 70),
        (70, 70),
        (50, 50),
        (20, 50),
        (80, 50),
        (50, 20),
        (50, 80)
    ]

    radii = [8] * 9

    clicks = []

    for center, radius in zip(centers, radii):
        clicks.append([
            center,
            (center[0] + radius, center[1])
        ])

    # Need two sets of clicks because the first attempt
    # will be rejected.
    clicks = iter(clicks + clicks)

    # First answer = n, second answer = y
    answers = iter(["n", "y"])

    monkeypatch.setattr(
        plt,
        "ginput",
        lambda n, timeout=-1: next(clicks)
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(answers)
    )

    selected_centers, selected_radii = manual_roi_selection(img)

    assert len(selected_centers) == 9
    assert len(selected_radii) == 9