from functions.relaxometry.generate_T2_map import generate_T2_map
import numpy as np

def test_generate_T2_map():
    # Create test data
    images = np.random.rand(32, 10, 10)
    TE_values = np.arange(15,481,15)

    # Generate T2 map
    T2_map = generate_T2_map(images, TE_values)

    # Assert the shape of the T2 map
    assert T2_map.shape == (10, 10)