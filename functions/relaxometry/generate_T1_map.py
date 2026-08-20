import numpy as np
from scipy.optimize import curve_fit

def generate_T1_map(images, TI_values, TR):
    """Define the exponential recovery function for T1 fitting with constant offset and magnitude image adjustment
    c * abs(1 - 2 * exp(-TI/T1) + exp(-TR/T1))"""
    print("Starting T1 fitting...")
    def exponential_recovery(TI, c, T1):
       return abs(c * (1 - 2 * np.exp(-TI / T1) + np.exp(-TR / T1)))
    #image dimensions:
    num_images, height, width = images.shape
    #initialise T1 map:
    T1_map = np.zeros((height, width))
    for i in range(height):
        for j in range(width):
            #Extract the pixel intensities for the current pixel from all images
            intensities = images[:, i, j].astype(float)

            #Initial guesses for I0 and T2
            initial_guess = [np.max(intensities), 600]
            #Perform non-linear fitting 
            try:
                # curve_fit returns (optimal_params, covariance_matrix)
                params, _ = curve_fit(
                    exponential_recovery, 
                    TI_values, 
                    intensities, 
                    p0=initial_guess,
                    bounds=([0, 1], [np.inf, 2000])
                  )
                T1_map[i, j] = params[1]
            except (RuntimeError, ValueError):
                # In case the fit fails to converge, set T1 to 0
                T1_map[i, j] = 0.0
    T1_map[(T1_map < 0) | (T1_map > 2000)] = 0.0
    print("T1 fitting complete. Close map to continue")
    return T1_map