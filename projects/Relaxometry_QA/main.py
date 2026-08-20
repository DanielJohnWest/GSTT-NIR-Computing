import tkinter as tk
from tkinter import filedialog as fd
import pydicom
import numpy as np
import cv2
from functions.relaxometry.manual_roi_selection import manual_roi_selection
from functions.relaxometry.prompt_input import prompt_input
from functions.relaxometry.generate_T1_map import generate_T1_map
from functions.relaxometry.generate_T2_map import generate_T2_map
from functions.relaxometry.find_rois import find_rois
from functions.relaxometry.calculate_roi_statistics import calculate_roi_statistics
from matplotlib import pyplot as plt
from matplotlib.patches import Circle
 

task = prompt_input('Which type of reconstruction would you like to perform: \n'
'1. T2 Mapping ME\n'
'2. T2 Mapping Clinical\n'
'3. T1 Mapping Multiple TI\n'
'4. T1 Mapping Clinical\n', 1, 4)
 
field = prompt_input(' What is the field strength of the scanner: \n\n'
                '1. 1.5T and below\n'
                '2. 3T and above\n', 1, 2)
 
if task in (1,2):
       if field == 2:
           reference_values = [42, 48, 167, 43, 49, 231, 43, 49, 133]#3T
       else:
           reference_values = [44, 48, 189, 45, 50, 243, 44, 48, 155]#1.5T
if task in (3,4):
        if field == 2:
            reference_values = [424, 1260, 451, 555, 1499, 1872, 294, 1010, 250] #3T
        else:
            reference_values = [430, 1090, 458, 562, 1333, 1489, 300, 803, 255] #1.5 T
#loading data
if task in (2,4):
    if task == 4:
        input('Please click enter and select the T1 clinical map')
        clin_map_locs = fd.askopenfilename()
        input('Please click enter and select the 1st image of the T1 clinical sequence')
        img1_loc = fd.askopenfilename()
    if task == 2:
        input('Please click enter and select the T2 clinical map')
        clin_map_locs = fd.askopenfilename()
        input('Please click enter and select the 1st image of the T2 clinical sequence')
        img1_loc = fd.askopenfilename()
    #read the dicom and turn into pixel array
    dcm_data = pydicom.dcmread(clin_map_locs)
    unscaled_pixels = dcm_data.pixel_array
    #rescale if rescale slope and intercept are in the dicom data. 
    #There is a built in module in pydicom that does this, but it only seems to work with certain versions
    try:
        slope = float(dcm_data.RescaleSlope)
        intercept = float(dcm_data.RescaleIntercept)
        tmap = (unscaled_pixels * slope) + intercept
    except AttributeError:
        tmap = unscaled_pixels
    img1 = pydicom.dcmread(img1_loc).pixel_array
if task == 1: 
    input('Please click enter and select 32 image of the T2 ME sequence') 
    while True: 
        try: 
            clin_map_locs = fd.askopenfilenames() 
            x = len(clin_map_locs) 
            if x == 32: 
                break 
            else: 
                print("Error: Select 32 images") 
        except:
                print("Select 32 images") 
    img1=pydicom.dcmread(clin_map_locs[0]).pixel_array 
    shape = np.shape(img1) 
    height, width = list(shape) 
    images = np.zeros((32, height, width)) 
    for i, file_path in enumerate(clin_map_locs): 
        images[i, :, :] = pydicom.dcmread(file_path).pixel_array
 
    # Echo times for the 32 images (TE values from 15ms to 480ms in 15ms intervals)
    TE_values = np.arange(15,481,15)
    # Generate the T2 map
    tmap = generate_T2_map(images, TE_values)
    img1 = images[0]
    plt.imshow(tmap)
    plt.show()

if task == 3:
    input('Please click enter and select the 6 images needed for T1 Mapping Multiple TI')
    while True:
        try:
            clin_map_locs = fd.askopenfilenames()
            x = len(clin_map_locs)
            if x == 6:
                break
            else:
                print("Error: Select 6 images")
        except:
            print("Select 6 images")
    img1=pydicom.dcmread(clin_map_locs[0]).pixel_array
    shape = np.shape(img1)
    height, width = list(shape)
    images = np.zeros((6, height, width))
    for i, file_path in enumerate(clin_map_locs):
        images[i, :, :] = pydicom.dcmread(file_path).pixel_array

    # Inversion times for the 6 images
    TI_values = np.array([50, 100, 200, 500, 1000, 2000])
    TR = 3000  # Repetition time in milliseconds
    # Generate the T1 map
    tmap = generate_T1_map(images, TI_values, TR)
    img1 = images[0]
    plt.imshow(tmap)
    plt.show()

# ROI Detection/Placement
roi_mode = prompt_input(
    "Choose ROI method:\n"
    "1. Automatic\n"
    "2. Manual\n"
    "Enter 1 or 2: ",
    1, 2
)

if roi_mode == 1:
    centers, radii, roi_mode = find_rois(img1, task)

    if roi_mode == 2:
        centers, radii = manual_roi_selection(img1)

else:
    centers, radii = manual_roi_selection(img1)

roi_means, roi_stds = calculate_roi_statistics(
    tmap,
    centers,
    radii
)
for i in range(9):
    print(
        f"ROI {i+1}: "
        f"Mean = {roi_means[i]:.2f}, "
        f"SD = {roi_stds[i]:.2f}"
    )