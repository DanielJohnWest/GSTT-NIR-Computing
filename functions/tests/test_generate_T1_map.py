from functions.relaxometry.generate_T1_map import generate_T1_map
import numpy as np

def test_generate_T1_map():
    # Create test data
    images = np.random.rand(6, 10, 10)
    TI_values = np.array([50, 100, 200, 500, 1000, 2000])
    TR = 3000

    # Generate T1 map
    T1_map = generate_T1_map(images, TI_values, TR)

    # Assert the shape of the T1 map
    assert T1_map.shape == (10, 10)