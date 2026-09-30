#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 15/02/2023

@author: oscarlally
"""

import os
import re
import json
import time
import shutil
import signal
import pydicom
import subprocess
import numpy as np
import nibabel as nib
from pathlib import Path
from shutil import rmtree


def check_dependencies(dependencies):
    try:
        # Run 'which' for the given command
        result = subprocess.run(
            ["which", 'mrcat'],
            capture_output=True,
            text=True,
            check=True
        )
        filepath = result.stdout.strip()

        if filepath:
            print('✅ The dependency mrtrix3 was found on system path.')
            dependencies['mrtrix'] = True

    except subprocess.CalledProcessError:
        print(
            "❌ Error finding mrtrix on system path. The code will attempt to run regardless, but this could cause issues")

    try:
        # Run 'which' for the given command
        result = subprocess.run(
            ["which", 'flirt'],
            capture_output=True,
            text=True,
            check=True
        )
        filepath = result.stdout.strip()

        if filepath:
            print('✅ The dependency fsl was found on system path.')
            dependencies['fsl'] = True

    except subprocess.CalledProcessError:
        print(
            f"❌ Error finding fsl on system path. The code will attempt to run regardless, but this could cause issues")

    return dependencies


def find_dir(pid, base_dir):
    x = 0
    for root, subdirs, files in os.walk(base_dir):
        if os.path.abspath(root) == f"{os.getcwd()}/mrtrix3_files/":
            continue
        for d in subdirs:
            if d == pid:
                x += 1
                return os.path.join(root, d)

    if x == 0:
        print('Please retype patient ID:')
        new_pid = input()
        return find_dir(new_pid, base_dir)


def cache_check(pid, base_dir):
    # Load existing JSON
    with open("./cache.json", "r") as f:
        data = json.load(f)

    stored = data["stored_patient_directories"]

    # Check if any stored directory matches the pid
    for directory in stored:
        if pid in directory[0]:
            if os.path.isdir(directory[0]):
                return directory[0]
            else:
                # Directory exists in cache but not on disk -> update
                new_directory = find_dir(pid, base_dir)
                stored[:] = [item for item in stored if item[0] != directory[0]]
                stored.append([new_directory])
                break
    else:
        # If no matching directory was found at all
        new_directory = find_dir(pid, base_dir)
        stored.append([new_directory])

    # Save back to JSON
    with open("./cache.json", "w") as f:
        json.dump(data, f, indent=4)

    return stored[-1][0]  # return the latest directory found


def add_reg_to(reg_to_file, pid):
    # Load existing JSON
    with open("./cache.json", "r") as f:
        data = json.load(f)
    stored = data["stored_patient_directories"]

    for directory in stored:
        if pid in directory[0] and len(directory) == 1:
            directory.append(reg_to_file)

    # Save the modified data back to the file
    with open("./cache.json", "w") as f:
        json.dump(data, f, indent=4)


def amend_filenames(folder):
    for filepath_end in os.listdir(folder):
        filepath = f"{folder}/{filepath_end}"
        path = Path(filepath)

        # Skip if it's a directory
        if path.is_dir():
            continue

        has_ext = bool(os.path.splitext(filepath)[1])
        if not has_ext:
            new_path = path.with_suffix('.dcm')
            path.rename(new_path)


def check_and_handle_directories(dir_list, pid):
    temp_root = f"./mrtrix3_files/{pid}/temp"
    os.makedirs(temp_root, exist_ok=True)

    for directory in dir_list:
        if not os.path.exists(directory):
            # Create directory if it doesn't exist
            print(f"Creating directory: {directory}")
            os.makedirs(directory)
        else:
            # Directory exists
            if os.listdir(directory) and directory != temp_root:
                # Directory is not empty
                print(f"The directory '{directory}' exists and is not empty.")
                while True:
                    choice = input(f"Do you want to delete its contents and recreate it? (y/n): ").lower()
                    if choice == 'y':
                        # Backup before deletion
                        timestamp = time.strftime("%Y%m%d-%H%M%S")
                        backup_dir = os.path.join(temp_root, f"{os.path.basename(directory)}_{timestamp}")
                        print(f"Backing up '{directory}' to '{backup_dir}'...")
                        shutil.copytree(directory, backup_dir)

                        # Delete and recreate the directory
                        print(f"Deleting contents of {directory} and recreating it.")
                        shutil.rmtree(directory)
                        os.makedirs(directory)
                        break
                    elif choice == 'n':
                        print(f"Leaving the directory '{directory}' as is.")
                        break
                    else:
                        print("Invalid input. Please enter 'y' or 'n'.")
            else:
                print(f"The directory '{directory}' exists and is empty.")


def get_full_file_names(directory_path):
    """Retrieve full file paths while excluding hidden files."""
    if not os.path.isdir(directory_path):
        print(f"Directory {directory_path} does not exist.")
        return []
    file_names = [f for f in os.listdir(directory_path) if not f.startswith('.')]
    full_file_names = [os.path.join(directory_path, file) for file in file_names]
    return full_file_names


def delete_files_in_folder(folder_path):
    """Deletes all files in a specified folder."""
    if os.path.isdir(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f'Deleted: {file_path}')
    else:
        print(f'The path {folder_path} is not a valid directory.')


class TimeoutException(Exception):
    pass


def find_app(application, dir_1, dir_2, timeout_duration=5):
    def find(application, dir, statement):
        x = 0
        for root, subdirs, files in os.walk(dir):
            for d in subdirs:
                if d == application:
                    x += 1
                    if x != 0:
                        a = os.path.join(root, d)
                        if a != None:
                            return os.path.join(root, d)
                        else:
                            print(statement)

    def timeout_handler(signum, frame):
        raise TimeoutException("Function timed out")

    result = None
    statement = "Could not find in first directory, trying another"
    for i in range(2):
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_duration)
            result = find(application, dir_1 if i == 0 else dir_2, statement)
            signal.alarm(0)
        except TimeoutException:
            print(f"Timed out while searching {'first' if i == 0 else 'second'} directory")
            result = None
        if result is not None:
            break
    return result

    if result is None:
        print(
            "The application is not in your user directory or your local directory. Please move it to either of these directories")


def run_unknown(cmd):
    # Initialise memory once
    if not hasattr(run_unknown, "dependency_paths"):
        run_unknown.dependency_paths = {'mrtrix': False, 'fsl': False}
        run_unknown.dependency_commands = {'mrtrix': False, 'fsl': False}

        home_dir = os.path.expanduser("~")

        if not run_unknown.dependency_paths['mrtrix']:
            run_unknown.dependency_paths['mrtrix'] = f"{find_app('mrtrix3', '/usr/local/', home_dir)}/bin"
        if not run_unknown.dependency_paths['fsl']:
            run_unknown.dependency_paths['fsl'] = f"{find_app('fsl', '/usr/local/', home_dir)}/bin"

        if not run_unknown.dependency_commands['mrtrix']:
            run_unknown.dependency_commands['mrtrix'] = os.listdir(run_unknown.dependency_paths['mrtrix'])
        if not run_unknown.dependency_commands['fsl']:
            run_unknown.dependency_commands['fsl'] = os.listdir(run_unknown.dependency_paths['fsl'])

    current_dir = os.getcwd()
    cmd_name = cmd.split()[0].strip()

    # Switch directory based on command
    if cmd_name in run_unknown.dependency_commands['mrtrix']:
        os.chdir(run_unknown.dependency_paths['mrtrix'])
    elif cmd_name in run_unknown.dependency_commands['fsl']:
        os.chdir(run_unknown.dependency_paths['fsl'])

    # Run process
    process = subprocess.run(cmd.split())

    # Restore working dir
    os.chdir(current_dir)

    return process


def run(*args):
    process = subprocess.run(args[0].split())


def register_pre_images(diff_data_dir, file_paths):
    for i in get_full_file_names(diff_data_dir):
        if 't1' in i.lower() and 'post' not in i.lower():
            t1_file = get_full_file_names(i)[0]
            shutil.copy(t1_file, file_paths['template_file_t1'])
            run(f"mrconvert {t1_file} {file_paths['t1_mif']} -force")
            run(f"mrconvert -strides -1,2,3 {t1_file} {file_paths['t1_nii']}")
        if 't1' in i.lower() and 'post' in i.lower():
            t1_post_file = get_full_file_names(i)[0]
            shutil.copy(t1_post_file, file_paths['template_file_t1_post'])
            run(f"mrconvert {t1_post_file} {file_paths['t1_post_mif']} -force")
            run(f"mrconvert -strides -1,2,3 {t1_post_file} {file_paths['t1_post_nii']}")
        if 'dark' in i.lower() or 'flair' in i.lower():
            flair_file = f"{get_full_file_names(i)[0]}"
            shutil.copy(flair_file, file_paths['template_file_flair'])
            run(f"mrconvert -strides -1,2,3 {flair_file} {file_paths['flair_file_nii']}")
        if 't2' in i.lower() and 'dark' not in i.lower() and 'flair' not in i.lower():
            t2_file = f"{get_full_file_names(i)[0]}"
            shutil.copy(t2_file, file_paths['template_file_t2'])
            run(f"mrconvert -strides -1,2,3 {t2_file} {file_paths['t2_file_nii']}")

    display_reg_files = [file_paths['t1_post_nii'], file_paths['t1_nii'], file_paths['flair_file_nii'],
                         file_paths['t2_file_nii']]
    display_reg_check = [os.path.isfile(x) for x in display_reg_files]

    "Register the files to one of the t1 images, preferentially the post."
    print("The data acquired have the following formats:")

    indices_to_remove = []
    for idx, i in enumerate(display_reg_check):
        if not i:
            indices_to_remove.append(idx)
    for i in indices_to_remove[::-1]:
        display_reg_files.pop(i)


    for idx, i in enumerate(display_reg_files):
        print(f"{idx + 1}. {i.split('/')[-1]} shape: {nib.load(i).shape}")

    print()
    while True:
        register_basis = int(
            input("Please type in the number of the file you want everything else to be registered to:  "))
        if 1 <= register_basis <= len(display_reg_files):
            break
        else:
            print("Invalid response, please try again.")
            print()

    register_to_file = display_reg_files[register_basis - 1]

    "Remove the file we are registering to and their status as a filepath"
    display_reg_files.remove(register_to_file)
    for reg_path in display_reg_files:
        if 'flair' in reg_path:
            flirt_cmd = f"flirt -in {reg_path} \
            -ref {register_to_file} \
            -omat {file_paths['flirt_transform']} \
            -out {file_paths['reg_flair_file']}"
            run(flirt_cmd)
        if 'post' in reg_path:
            flirt_cmd = f"flirt -in {reg_path} \
            -ref {register_to_file} \
            -omat {file_paths['t1_transform']} \
            -out {file_paths['reg_t1_post_file']}"
            run(flirt_cmd)
        if 't1' in reg_path and 'post' not in reg_path:
            flirt_cmd = f"flirt -in {reg_path} \
            -ref {register_to_file} \
            -omat {file_paths['t1_transform']} \
            -out {file_paths['reg_t1_file']}"
            run(flirt_cmd)
        if 't2' in reg_path:
            flirt_cmd = f"flirt -in {reg_path} \
            -ref {register_to_file} \
            -omat {file_paths['t1_transform']} \
            -out {file_paths['reg_t2_file']}"
            run(flirt_cmd)

    return register_to_file


def tensor_reg(reg_to, fa, ev, pid, mif_reg):
    fa_reg = f"{os.getcwd()}/mrtrix3_files/{pid}/tensors/fa_reg.mif"
    ev_reg = f"{os.getcwd()}/mrtrix3_files/{pid}/tensors/ev_reg.mif"
    warp_reg = f"{os.getcwd()}/mrtrix3_files/{pid}/tensors/warp.mif"
    conv_reg_to = f"mrconvert {reg_to} {mif_reg}"
    print(conv_reg_to)
    run(conv_reg_to)
    conv_fa_cmd = f"mrregister {fa} {mif_reg} - rigid - transformed {fa_reg} - nl_warp {warp_reg}"
    conv_ev_cmd = f"mrtransform {ev} - warp {warp_reg} - reorient_fod yes {ev_reg}"
    run(conv_fa_cmd)
    run(conv_ev_cmd)
    return fa_reg, ev_reg

    run(flirt_cmd)
def get_counts(tck_image):
    cmd = f"tckinfo -count {tck_image}"
    result = subprocess.run(cmd.split(), capture_output=True, text=True)

    output = result.stdout

    last_line = output.split('\n')[-2:-1]

    match = re.search(r'\d+', last_line[0])

    if match:
        number = int(match.group())

    out_file = tck_image.split('/')[-1]

    print(f"Actual Tract Count in {out_file} is {number}")

    return int(number)


def get_shape(nii_file_list):
    if isinstance(nii_file_list, list):
        for idx, i in enumerate(nii_file_list):
            print(f"{idx + 1}. {i.split('/')[-1]} shape: {nib.load(i).shape}")
    else:
        if 'dcm' in nii_file_list:
            data = pydicom.dcmread(nii_file_list)
            return data.pixel_array.shape
        elif 'nii' in nii_file_list:
            return nib.load(nii_file_list).shape


def convert_tracts(nii_file, debug, pid):
    current_dir = os.getcwd()
    nii_dir = f"{current_dir}/mrtrix3_files/{pid}/nifti/"
    tract_dir = f"{current_dir}/mrtrix3_files/{pid}/tracts/"
    fa_tensor = f"{current_dir}/mrtrix3_files/{pid}/tensors/fa.mif"

    tract_files = []
    dir_files = os.listdir(tract_dir)
    for i in dir_files:
        if '.tck' in i:
            tract_files.append(f"{i}")

    for i in tract_files:
        mif_file = f"{tract_dir}{i.split('.')[0]}.mif"
        tck_file = f"{tract_dir}{i.split('.')[0]}.tck"
        norm_file = f"{tract_dir}{i.split('.')[0]}_NORM.mif"
        tck_to_mif = f"tckmap -template {fa_tensor} {tck_file} {mif_file} -force"
        run(tck_to_mif)
        N_tracts = get_counts(f"{tract_dir}{i}")
        run(f"mrcalc {mif_file} {N_tracts} -div {norm_file} -force")
        if debug == 'debug':
            mrview_cmd = f"mrview -mode 2 -load {nii_file} -interpolation 0 -overlay.load {norm_file} -comments 0"
            run(mrview_cmd)
        norm_nii_file = f"{nii_dir}{i.split('.')[0]}_NORM.nii"
        run(f"mrconvert -strides -1,2,3 {norm_file} {norm_nii_file} -axes 0,1,2 -force")

        t1_bet_file = f"{nii_file.split('.')[0]}_bet.nii.gz"
        bet_cmd = f"bet {nii_file} {t1_bet_file} -n -m"
        run(bet_cmd)


def get_volumes(mif_image):
    cmd = f"mrinfo -size {mif_image}"
    result = subprocess.run(cmd.split(), capture_output=True, text=True)

    if result.returncode == 0:
        size_str = result.stdout.strip()
        size = tuple(map(int, size_str.split()))
        print(f"Image dimensions: {size}")
    else:
        print(f"Error: {result.stderr.strip()}")

    output = result.stdout
    print(output)
    volumes = int(output.split(' ')[-1])

    return volumes


def masking(dwi_cmd, mr_conv_1_cmd, mr_conv_2_cmd, debug, pid):
    current_dir = os.getcwd()
    run(dwi_cmd)
    run(mr_conv_1_cmd)
    run(mr_conv_2_cmd)

    b0_extract_nii = f"{current_dir}/mrtrix3_files/{pid}/masking/extracted_b0.nii"
    moved_b0_extract_nii = f"{current_dir}/mrtrix3_files/{pid}/nifti/extracted_b0.nii"
    b0_upsamp = f"{current_dir}/mrtrix3_files/{pid}/masking/b0_upsamp.nii.gz"
    b0_upsamp_mask = f"{current_dir}/mrtrix3_files/{pid}/masking/b0_upsamp_mask.nii.gz"

    # Ensure the 'nifti' directory exists
    os.makedirs(os.path.dirname(moved_b0_extract_nii), exist_ok=True)
    shutil.copy(b0_extract_nii, moved_b0_extract_nii)

    g = input("g-value vertical gradient in fractional intensity threshold (-1->1); default=0: ")
    f = input("f-value fractional intensity threshold (0->1); default=0.5: ")

    bet_cmd = f"bet {b0_extract_nii} {b0_upsamp} -n -m -f {f} -g {g}"
    run(bet_cmd)

    if debug == 'debug':
        print('Check if the mask has worked. If it has not, re-run this script or check_mask function in mask.py.')
        fsleyes_path = os.environ.get('FSLDIR')
        fsleyes_bin = f"{fsleyes_path}/bin/fsleyes"
        fsl_cmd = f"{fsleyes_bin} {b0_extract_nii} {b0_upsamp_mask}"
        subprocess.run(fsl_cmd.split())
        os.chdir(current_dir)

    os.rename(b0_upsamp_mask, f"{current_dir}/mrtrix3_files/{pid}/masking/mask_final.nii.gz")
    with open(f"{current_dir}/mrtrix3_files/{pid}/masking/mask_params.txt", 'a') as param_file:
        param_file.write(f"The g-value is {g} and f-value is {f}\n")


def create_mask(nii_list, debug, pid):
    current_dir = os.getcwd()
    upsample_out = f"{current_dir}/mrtrix3_files/{pid}/eddy/dwi_eddy_upsamp.mif"
    b0_extract = f"{current_dir}/mrtrix3_files/{pid}/masking/extracted_b0.mif"
    b0_1_extract = f"{current_dir}/mrtrix3_files/{pid}/masking/extracted_b0_1.mif"
    b0_extract_nii = f"{current_dir}/mrtrix3_files/{pid}/masking/extracted_b0.nii"
    mask_final = f"{current_dir}/mrtrix3_files/{pid}/masking/mask_final.nii.gz"
    mask_mif = f"{current_dir}/mrtrix3_files/{pid}/masking/mask_final.mif"

    nii_list.append(b0_extract_nii)

    if not os.path.exists(mask_mif):
        dwi_cmd = f"dwiextract -bzero {upsample_out} {b0_extract} -force"
        mr_conv_1_cmd = f"mrconvert {b0_extract} {b0_1_extract} -coord 3 0 -axes 0,1,2"
        mr_conv_2_cmd = f"mrconvert -strides -1,2,3 {b0_1_extract} {b0_extract_nii}"

        masking(dwi_cmd, mr_conv_1_cmd, mr_conv_2_cmd, debug, pid)

        continue_yn = input('Mask correct and continue with analysis? (y/n): ')
        if continue_yn.lower() != 'y':
            rmtree(f"{current_dir}/mrtrix3_files/{pid}/masking/")
            os.makedirs(f"{current_dir}/mrtrix3_files/{pid}/masking/")
            create_mask(nii_list, debug, pid)
        else:
            print('Mask Successfully Made')
    else:
        mask_input = input("Are you sure you want to create a new mask? (y/n): ")
        if mask_input.lower() == 'y':
            dwi_cmd = f"dwiextract -bzero {upsample_out} {b0_extract} -force"
            mr_conv_1_cmd = f"mrconvert {b0_extract} {b0_1_extract} -coord 3 0 -axes 0,1,2"
            mr_conv_2_cmd = f"mrconvert -strides -1,2,3 {b0_1_extract} {b0_extract_nii}"

            masking(dwi_cmd, mr_conv_1_cmd, mr_conv_2_cmd, debug, pid)

            continue_yn = input('Mask correct and continue with analysis? (y/n): ')
            if continue_yn.lower() != 'y':
                rmtree(f"{current_dir}/mrtrix3_files/{pid}/masking/")
                os.makedirs(f"{current_dir}/mrtrix3_files/{pid}/masking/")
                create_mask(nii_list, debug)
            else:
                print('Mask Successfully Made')


def tensor_estimation(DWI_shell, debug, pid):
    current_dir = os.getcwd()
    mask_final = f"{current_dir}/mrtrix3_files/{pid}/masking/mask_final.nii.gz"
    mask_mif = f"{current_dir}/mrtrix3_files/{pid}/masking/mask_final.mif"
    mr_conv_3_cmd = f"mrconvert {mask_final} {mask_mif}"
    run(mr_conv_3_cmd)

    response_wm = f"{current_dir}/mrtrix3_files/{pid}/response/response_wm.txt"
    response_gm = f"{current_dir}/mrtrix3_files/{pid}/response/response_gm.txt"
    response_csf = f"{current_dir}/mrtrix3_files/{pid}/response/response_csf.txt"
    response_voxels = f"{current_dir}/mrtrix3_files/{pid}/response/response_voxels.mif"

    """TENSOR ESTIMATION"""

    upsample_out = f"{current_dir}/mrtrix3_files/{pid}/eddy/dwi_eddy_upsamp.mif"
    dwi_tensor = f"{current_dir}/mrtrix3_files/{pid}/tensors/dwi_tensor.mif"
    fa_tensor = f"{current_dir}/mrtrix3_files/{pid}/tensors/fa.mif"
    ev_tensor = f"{current_dir}/mrtrix3_files/{pid}/tensors/ev.mif"
    fa_nii = f"{current_dir}/mrtrix3_files/{pid}/tensors/fa.nii.gz"

    if not os.path.exists(dwi_tensor):
        print("Step 7: Tensor estimation")
        dwi2tensor_cmd = f"dwi2tensor {upsample_out} {dwi_tensor} -mask {mask_mif}"
        tens2metr_cmd = f"tensor2metric -mask {mask_mif} -fa {fa_tensor} -vector {ev_tensor} {dwi_tensor}"
        conv_fa = f"mrconvert {fa_tensor} {fa_nii}"
        run(dwi2tensor_cmd)
        run(tens2metr_cmd)
        run(conv_fa)

    if debug == 'debug':
        print("DEBUG STEP: Check the FA and EV maps")
        # mrview_tensor = f"mrview -load {fa_tensor} -interpolation 0 -load {ev_tensor} -interpolation 0 -odf.load_tensor {dwi_tensor}"
        mrview_tensor = f"mrview -load {fa_tensor} -interpolation 0 -load {ev_tensor} -interpolation 0"
        run(mrview_tensor)

    wm_fod = f"{current_dir}/mrtrix3_files/{pid}/fods/wm_fod.mif"
    wm_fod_int = f"{current_dir}/mrtrix3_files/{pid}/fods/wm_fod_int.mif"
    csf_fod = f"{current_dir}/mrtrix3_files/{pid}/fods/csf_fod.mif"
    gm_fod = f"{current_dir}/mrtrix3_files/{pid}/fods/gm_fod.mif"
    tissue_vf = f"{current_dir}/mrtrix3_files/{pid}/fods/tissue_vf.mif"

    # Perform multi shell multi tissue constrained spherical deconvolution
    if DWI_shell.lower() == 'n':
        print("Single shell data")
        dwi2fod_cmd = f"dwi2fod msmt_csd -mask {mask_mif} {upsample_out} {response_wm} {wm_fod} {response_csf} {csf_fod} "
        run(dwi2fod_cmd)
    elif DWI_shell.lower() == 'y':
        print("Multi-shell data")
        dwi2fod_cmd = f"dwi2fod msmt_csd -mask {mask_mif} {upsample_out} {response_wm} {wm_fod} {response_gm} {gm_fod} {response_csf} {csf_fod} "
        run(dwi2fod_cmd)
        mrconv_cmd = f"mrconvert {wm_fod} {wm_fod_int} -coord 3 0"
        run(mrconv_cmd)
        mrcat_cmd = f"mrcat {csf_fod} {gm_fod} {wm_fod_int} {tissue_vf}"
        run(mrcat_cmd)
        if debug == 'debug':
            mrview_cmd = f"mrview -mode 2 -load {tissue_vf} -interpolation 0"
            run(mrview_cmd)


def get_nii_file(pid):
    with open("./cache.json", "r") as f:
        data = json.load(f)
    stored = data["stored_patient_directories"]
    for directory in stored:
        if pid in directory[0]:
            return directory[1]


def binarise_numpy(input_file, inv = True):
    img = nib.load(input_file)
    array = img.get_fdata()

    if inv:
        binary = (array == 0).astype(np.uint8)
    else:
        binary = (array != 0).astype(np.uint8)

    return binary


def copy_directory(source_dir, destination_dir):
    try:
        # Ensure the destination directory exists
        target_path = os.path.join(destination_dir, os.path.basename(source_dir))

        # Check if the directory already exists
        if os.path.exists(target_path):
            print(f"Directory {target_path} already exists. Deleting it...")
            shutil.rmtree(target_path)  # Remove the existing directory

        # Copy the entire directory
        shutil.copytree(source_dir, target_path)
        print(f"Directory copied from {source_dir} to {destination_dir}")
    except Exception as e:
        print(f"An error occurred: {e}")


def safe_copy(src, dst_dir):
    """
    Copies a file into dst_dir.
    If src and dst resolve to the same path, append _1, _2, etc. until unique.
    """
    os.makedirs(dst_dir, exist_ok=True)  # make sure the directory exists

    filename = os.path.basename(src)
    dst = os.path.join(dst_dir, filename)

    # If destination exists or resolves to same file, generate a new name
    if os.path.exists(dst):
        # Only check samefile if dst exists (prevents FileNotFoundError)
        if os.path.samefile(src, dst):
            base, ext = os.path.splitext(filename)
            i = 1
            while True:
                new_filename = f"{base}_{i}{ext}"
                new_dst = os.path.join(dst_dir, new_filename)
                if not os.path.exists(new_dst):
                    dst = new_dst
                    break
                i += 1
        else:
            # dst exists but is not the same file → also rename
            base, ext = os.path.splitext(filename)
            i = 1
            while True:
                new_filename = f"{base}_{i}{ext}"
                new_dst = os.path.join(dst_dir, new_filename)
                if not os.path.exists(new_dst):
                    dst = new_dst
                    break
                i += 1

    shutil.copyfile(src, dst)
    return dst  # return the final path copied to