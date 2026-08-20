import numpy as np
from scipy.optimize import curve_fit

def generate_T2_map(images, TE_values):
    print("Starting T2 fitting...")
    #Define the exponential decay function inside the local scope
    def exponential_decay(TE, I0, T2):
        return I0 * np.exp(-TE / T2)
    #Get the dimensions of the images
    num_images, height, width = images.shape
    #Initialize the T2 map
    T2_map = np.zeros((height, width))
    #Loop through each pixel in the image
    for i in range(height):
        for j in range(width):
            #Extract the pixel intensities for the current pixel from all images
            intensities = images[:, i, j].astype(float)

            # Don't attempt to fit pixels with no signal
            if np.max(intensities) <= 0:
                continue

            #Initial guesses for I0 and T2
            initial_guess = [np.max(intensities), 30.0]
            #Perform non-linear fitting
            try:
                # curve_fit returns (optimal_params, covariance_matrix)
                params, _ = curve_fit(
                    exponential_decay, 
                    TE_values, 
                    intensities, 
                    p0=initial_guess,
                    bounds=([0, 1], [np.inf, 300])
                  )
                T2_map[i, j] = params[1]
            except RuntimeError:
                # In case the fit fails to converge, set T2 to 0
                T2_map[i, j] = 0.0
    T2_map[(T2_map < 0) | (T2_map > 300)] = 0.0
    print("T2 fitting complete. Close map to continue")
    return T2_map