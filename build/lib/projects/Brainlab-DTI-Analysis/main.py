import os
import shutil
import pydicom
import numpy as np
import nibabel as nib
from final_dcm import create_brainlab_object
from tract_roi_match import roi_table
from functions import (check_and_handle_directories, \
    get_full_file_names, \
    register_pre_images, \
    add_reg_to, \
    amend_filenames, \
    get_shape, \
    get_volumes, \
    create_mask, \
    cache_check, \
    safe_copy, \
    tensor_reg, \
    binarise_numpy,\
    tensor_estimation, \
    get_nii_file, \
    convert_tracts, \
    copy_directory, \
    check_dependencies)
from register import registration
from intro import intro
from generate_tracts import run_tract_generation
from tract_check import tract_selection_check

# Check fsl and mrtrix dependencies
dependencies = {'mrtrix': False, 'fsl': False}
dependencies = check_dependencies(dependencies)

if dependencies['mrtrix'] and dependencies['fsl']:
    from functions import run
else:
    from functions import run_unknown as run


# Define data directories
home_dir = os.path.expanduser("~")
print("This code only runs automatically provided there is a UNIQUE folder with the patient ID")
pid = input('Please type in the patient number:  ')
diff_data_dir = cache_check(pid, home_dir)

# Convert to .dcm if needs be
diff_data_dirs = os.listdir(diff_data_dir)
if '.DS_Store' in diff_data_dirs:
    diff_data_dirs.remove('.DS_Store')

for images in diff_data_dirs:
    if 'processed' not in images.lower():
        amend_filenames(f"{diff_data_dir}/{images}")



def main():
    intro()
    step = int(input('Please type in the step you would like to start on:  '))
    cont = 'y'

    # Centralized dictionary for all file paths
    file_paths = {
        "output_dirs": [
            f"mrtrix3_files/{pid}/converted",
            f"mrtrix3_files/{pid}/concatenated",
            f"mrtrix3_files/{pid}/denoised",
            f"mrtrix3_files/{pid}/calc",
            f"mrtrix3_files/{pid}/degibbs",
            f"mrtrix3_files/{pid}/eddy",
            f"mrtrix3_files/{pid}/response",
            f"mrtrix3_files/{pid}/masking",
            f"mrtrix3_files/{pid}/tensors",
            f"mrtrix3_files/{pid}/fods",
            f"mrtrix3_files/{pid}/misc",
            f"mrtrix3_files/{pid}/rois",
            f"mrtrix3_files/{pid}/tracts",
            f"mrtrix3_files/{pid}/t1",
            f"mrtrix3_files/{pid}/overlays",
            f"mrtrix3_files/{pid}/volumes",
            f"mrtrix3_files/{pid}/template",
            f"mrtrix3_files/{pid}/nifti"
        ],
        "converted": [],
        "b0": None,
        "b0_rev": None,
        "concat_file": f"{os.getcwd()}/mrtrix3_files/{pid}/concatenated/combined_dwi.mif",
        "denoise_file": f"{os.getcwd()}/mrtrix3_files/{pid}/denoised/denoised_dwi.mif",
        "denoise_ap": f"{os.getcwd()}/mrtrix3_files/{pid}/denoised/denoised_ap.mif",
        "denoise_pa": f"{os.getcwd()}/mrtrix3_files/{pid}/denoised/denoised_pa.mif",
        "resid_output": f"{os.getcwd()}/mrtrix3_files/{pid}/calc/dwi_denoise_residuals.mif",
        "degibbs_file": f"{os.getcwd()}/mrtrix3_files/{pid}/degibbs/dwi_degibbs.mif",
        "template_file": f"{os.getcwd()}/mrtrix3_files/{pid}/template/template.dcm",
        "alt_template_file": f"{os.getcwd()}/mrtrix3_files/{pid}/template/alt_template.dcm",
        "template_file_t2": f"{os.getcwd()}/mrtrix3_files/{pid}/template/template_t2.dcm",
        "template_file_flair": f"{os.getcwd()}/mrtrix3_files/{pid}/template/template_flair.dcm",
        "template_file_t1": f"{os.getcwd()}/mrtrix3_files/{pid}/template/template_t1.dcm",
        "template_file_t1_post": f"{os.getcwd()}/mrtrix3_files/{pid}/template/template_t1_post.dcm",
        "flair_file_nii": f"{os.getcwd()}/mrtrix3_files/{pid}/nifti/flair.nii",
        "t2_file_nii": f"{os.getcwd()}/mrtrix3_files/{pid}/nifti/t2.nii",
        "reg_flair_file": f"{os.getcwd()}/mrtrix3_files/{pid}/nifti/reg_flair.nii.gz",
        "reg_t2_file": f"{os.getcwd()}/mrtrix3_files/{pid}/nifti/reg_t2.nii.gz",
        "reg_t1_post_file": f"{os.getcwd()}/mrtrix3_files/{pid}/nifti/reg_t1_post.nii.gz",
        "reg_t1_file": f"{os.getcwd()}/mrtrix3_files/{pid}/nifti/reg_t1.nii.gz",
        "t1_nii": f"{os.getcwd()}/mrtrix3_files/{pid}/nifti/t1.nii",
        "t1_mif": f"{os.getcwd()}/mrtrix3_files/{pid}/converted/t1.mif",
        "t1_post_nii": f"{os.getcwd()}/mrtrix3_files/{pid}/nifti/t1_post.nii",
        "t1_post_mif": f"{os.getcwd()}/mrtrix3_files/{pid}/converted/t1_post.mif",
        "degibbs_ap_file": f"{os.getcwd()}/mrtrix3_files/{pid}/degibbs/dwi_degibbs_ap.mif",
        "flirt_transform": f"{os.getcwd()}/mrtrix3_files/{pid}/misc/flair_to_t1.mat",
        "t1_transform": f"{os.getcwd()}/mrtrix3_files/{pid}/misc/t1_to_t1.mat",
        "degibbs_pa_file": f"{os.getcwd()}/mrtrix3_files/{pid}/degibbs/dwi_degibbs_pa.mif",
        "degibbs_pair_file": f"{os.getcwd()}/mrtrix3_files/{pid}/degibbs/degibbs_pair.mif",
        "degibbs_ap_n": f"{os.getcwd()}/mrtrix3_files/{pid}/degibbs/b0_AP_degibbs_N.mif",
        "degibbs_ap_pa_n": f"{os.getcwd()}/mrtrix3_files/{pid}/degibbs/b0_AP_PA_degibbs_N.mif",
        "eddy_file": f"{os.getcwd()}/mrtrix3_files/{pid}/eddy/dwi_preprocessed_eddy.mif",
        "upsample_out": f"{os.getcwd()}/mrtrix3_files/{pid}/eddy/dwi_eddy_upsamp.mif",
        "response_wm": f"{os.getcwd()}/mrtrix3_files/{pid}/response/response_wm.txt",
        "response_gm": f"{os.getcwd()}/mrtrix3_files/{pid}/response/response_gm.txt",
        "response_csf": f"{os.getcwd()}/mrtrix3_files/{pid}/response/response_csf.txt",
        "response_voxels": f"{os.getcwd()}/mrtrix3_files/{pid}/response/response_voxels.mif",
        "fa": f"{os.getcwd()}/mrtrix3_files/{pid}/tensors/fa.mif",
        "ev": f"{os.getcwd()}/mrtrix3_files/{pid}/tensors/ev.mif",
        "dwi_tensor": f"{os.getcwd()}/mrtrix3_files/{pid}/tensors/dwi_tensor.mif",
        "nii_file": f"{os.getcwd()}/mrtrix3_files/{pid}/masking/extracted_b0.nii",
        "registered": []
    }


    # Ensure output directories exist
    # check_and_handle_directories(file_paths["output_dirs"], pid)

    b0s_check = get_full_file_names(f"{os.getcwd()}/mrtrix3_files/{pid}/converted")
    if len(b0s_check) != 0:
        for i in b0s_check:
            if 'b0' in i and 'flipped' in i:
                file_paths["b0_rev"] = i
            if 'b0' in i and 'flipped' not in i:
                file_paths["b0"] = i

    if int(step) == 1 and cont.lower() == 'y':
        print(diff_data_dir)
        # Convert diffusion files to .mif and categorize by type
        if any('ep2d' in f for f in get_full_file_names(diff_data_dir)):
            for i in get_full_file_names(diff_data_dir):
                if 'ep2d' in i.lower() and 'fa' not in i.lower():
                    convert = f"{os.getcwd()}/mrtrix3_files/{pid}/converted/{os.path.basename(i)}.mif"
                    result_cmd = f"mrconvert {i} {convert}"
                    run(result_cmd)
                    file_paths["converted"].append(convert)
                    if 'b0' in i.lower():
                        if 'flipped' in i.lower():
                            file_paths["b0_rev"] = convert
                        else:
                            file_paths["b0"] = convert
        else:
            for i in get_full_file_names(diff_data_dir):
                banned = ['fa', 't1', 'flair', 't2', 'dark']
                if all(word not in i.lower() for word in banned):
                    convert = f"{os.getcwd()}/mrtrix3_files/{pid}/converted/{os.path.basename(i)}.mif"
                    result_cmd = f"mrconvert {i} {convert}"
                    run(result_cmd)
                    file_paths["converted"].append(convert)
                    if 'b0' in i.lower():
                        if 'flipped' in i.lower():
                            file_paths["b0_rev"] = convert
                        else:
                            file_paths["b0"] = convert
        step += 1
        cont = 'y'

    if step == 2 and cont.lower() == 'y':
        "Create all of the .nii files to be registered"
        print()
        print('---------------------')
        print("Starting registration process due to multiple structural imaging datasets. Please wait...")
        file_reg_to = register_pre_images(diff_data_dir, file_paths)
        add_reg_to(file_reg_to, pid)
        print("Registration process completed successfully.")
        print()
        step += 1
        cont = 'y'

    if step == 3 and cont.lower() == 'y':
        # Concatenate diffusion files excluding `b0` or flipped files
        cat_cmd = "mrcat "
        cat_count = 0
        one_case = None
        for i in os.listdir(f'./mrtrix3_files/{pid}/converted'):
            banned = ['fa', 't1', 'flair', 't2', 'dark', 'flipped']
            if all(word not in i.lower() for word in banned):
                cat_count += 1
                cat_cmd += f'./mrtrix3_files/{pid}/converted/{i} '
                one_case = f'./mrtrix3_files/{pid}/converted/{i}'
                print(cat_count)
        if cat_count > 1:
            cat_cmd += f"{file_paths['concat_file']}"
            print(cat_cmd)
            run(cat_cmd)
        else:
            print("DEBUG concat_file:", file_paths.get('concat_file'))
            shutil.copy2(one_case, file_paths['concat_file'])
        extract_cmd = f"dwiextract {file_paths['concat_file']} {file_paths['b0']} -bzero -force"
        run(extract_cmd)
        step += 1
        cont = 'y'

    if step == 4 and cont.lower() == 'y':
        run(f"mrinfo {file_paths['b0']}")
        run(f"mrinfo {file_paths['b0_rev']}")

        # Denoise files
        run(f"dwidenoise {file_paths['concat_file']} {file_paths['denoise_file']}")
        run(f"dwidenoise {file_paths['b0']} {file_paths['denoise_ap']}")
        run(f"dwidenoise {file_paths['b0_rev']} {file_paths['denoise_pa']}")

        # Calculate residuals
        calc_cmd = f"mrcalc {file_paths['concat_file']} {file_paths['denoise_file']} -subtract {file_paths['resid_output']}"
        run(calc_cmd)
        step += 1
        cont = 'y'

    if step == 5 and cont.lower() == 'y':
        # Degibbs processing
        run(f"mrdegibbs {file_paths['denoise_pa']} {file_paths['degibbs_pa_file']}")
        run(f"mrdegibbs {file_paths['denoise_file']} {file_paths['degibbs_file']}")
        run(f"dwiextract -bzero {file_paths['degibbs_file']} {file_paths['degibbs_ap_file']}")

        pa_size = get_volumes(file_paths['degibbs_file'])
        ap_size = get_volumes(file_paths['degibbs_ap_file'])
        pa_size_pre = get_volumes(file_paths["b0_rev"])
        ap_size_pre = get_volumes(file_paths["b0"])

        if ap_size == pa_size == pa_size_pre == ap_size_pre:
            print(f"There are {pa_size} volumes in the PA image and there are {ap_size} volumes in the AP image.")

        # Concatenate degibbs files
        run(f"mrcat {file_paths['degibbs_ap_file']} {file_paths['degibbs_pa_file']} {file_paths['degibbs_pair_file']} -force")

        # Extract the last 2 * N_B0_PA images
        N_B0_PA = 4
        run(f"mrconvert {file_paths['degibbs_ap_file']} -coord 3 1:{N_B0_PA} {file_paths['degibbs_ap_n']} -quiet -force")
        run(f"mrcat {file_paths['degibbs_ap_n']} {file_paths['degibbs_pa_file']} {file_paths['degibbs_ap_pa_n']} -force")

        print()
        print('--------------------------')
        print('Please assess the processed files before running the eddy current correction.')
        run(f"mrview -load {file_paths['degibbs_ap_pa_n']} -interpolation 0")

        step += 1
        cont = input('Continue? (y/n): ')

    if step == 6 and cont.lower() == 'y':
        # Eddy current corrections
        preproc_cmd = f"dwifslpreproc {file_paths['degibbs_file']} {file_paths['eddy_file']} -rpe_pair -se_epi {file_paths['degibbs_ap_pa_n']} -pe_dir ap -force"
        print(preproc_cmd)
        run(preproc_cmd)

        mrgrid_cmd = f"mrgrid {file_paths['eddy_file']} regrid -voxel 1.3 {file_paths['upsample_out']} -force"
        run(mrgrid_cmd)

        step += 1
        cont = input('Continue? (y/n): ')

    if step == 7 and cont.lower() == 'y':
        # Get response functions
        if not os.path.exists(file_paths['response_wm']):
            print("Step 7: Response function")
            # Estimate the response functions for WM, GM, and CSF
            dwi2response_cmd = (
                f"dwi2response dhollander {file_paths['upsample_out']} {file_paths['response_wm']} "
                f"{file_paths['response_gm']} {file_paths['response_csf']} -voxels {file_paths['response_voxels']} -force"
            )
            run(dwi2response_cmd)

        run(f"shview {file_paths['response_wm']}")
        run(f"shview {file_paths['response_gm']}")
        run(f"shview {file_paths['response_csf']}")

        print("Check the voxels are assigned to the correct tissue types. RED = CSF, GREEN = GM, BLUE = WM")
        run(
            f"mrview -load {file_paths['upsample_out']} -interpolation 0 "
            f"-overlay.load {file_paths['response_voxels']} -overlay.interpolation 0"
        )

        step += 1
        cont = input('Continue? (y/n): ')

    if step == 8 and cont.lower() == 'y':
        # Masking
        nii_files = []
        create_mask(nii_files, 'debug', pid)
        file_paths[
            'nii_file'] = f"{os.getcwd()}/mrtrix3_files/{pid}/masking/extracted_b0.nii"

        step += 1
        cont = input('Continue? (y/n): ')

    if step == 9 and cont.lower() == 'y':
        # Tensors
        dwi_shell = input('Is the data multi-shelled? (y/n): ')
        tensor_estimation(dwi_shell, 'debug', pid)
        step += 1
        cont = input('Continue? (y/n): ')

    if step == 10 and cont.lower() == 'y':
        # Create ROIs
        print()
        print('-------------------------')
        print('The following tracts are created using the below ROIs.  Make sure to save the ROIs in this format for the code to be able to recognise them.')
        print()
        roi_table()
        print()
        print()
        print('-------------------------')

        while True:
            print('Please save any ROIs in the roi folder in the sub directory /mrtrix3/patient_number/rois that is in the directory of this code.')
            print('This should be obvious as one of the sub directories will appear at the top of the ROI editor.')
            print()
            choice = input('Do you need to create any ROIs? (y/n). ')
            print()
            print('Please save the ROI under the following names for the script to be able to find them'.upper())

            if choice.lower() == 'y':
                run('echo -e "Opening mrview"')
                message = "Step 10: Draw ROIs"
                message = "\033[32m" + message + "\033[0m"
                command = "echo {}".format(message)
                run(command)
                fa = file_paths['fa']
                ev = file_paths['ev']
                converted_nii_file = get_nii_file(pid)

                # check_reg = input("Do you want to register the fa and ev maps? (y/n): ")
                # if check_reg.lower() == 'y':
                #     # step size should be 0.5xvoxelsize (currently set to 1)
                #
                #     mif_reg = f"{os.getcwd()}/mrtrix3_files/{pid}/misc/t_reg.mif"
                #     if not os.path.exists(mif_reg):
                #         fa_reg, ev_reg = tensor_reg(converted_nii_file, fa, ev, pid, mif_reg)
                #     else:
                #         fa_reg = f"{os.getcwd()}/mrtrix3_files/{pid}/tensors/fa_reg.mif"
                #         ev_reg = f"{os.getcwd()}/mrtrix3_files/{pid}/tensors/ev_reg.mif"
                #
                #     view_cmd = f"mrview -mode 2 -load {fa_reg} -interpolation 0 -load {ev_reg} -interpolation 0 -comments 0 -overlay.load {converted_nii_file}"
                #     run(view_cmd)
                # else:
                #     view_cmd = f"mrview -mode 2 -load {fa} -interpolation 0 -load {ev} -interpolation 0 -comments 0 -overlay.load {converted_nii_file}"
                #     run(view_cmd)

                view_cmd = f"mrview -mode 2 -load {fa} -interpolation 0 -load {ev} -interpolation 0 -comments 0 -overlay.load {converted_nii_file}"
                run(view_cmd)

                break
            elif choice.lower() == 'n':
                print('Continue with analysis using ROIs already generated')
                break
            else:
                message = "Invalid response"
                message = "\033[31m" + message + "\033[0m"
                command = "echo {}".format(message)
                run(command)

        step += 1
        cont = input('Continue? (y/n): ')

    if step == 11 and cont.lower() == 'y':

        "Need to do wm reg"

        first_flag = True
        def create_tract(tract_selection_no, first_flag, pid):
            while True:
                tract_path, check = run_tract_generation(pid, tract_selection_no, first_flag, False)
                if check.lower() == 'y':
                    return tract_path  # exit cleanly
                else:
                    first_flag = False

        tract_names = []
        while True:
            tract_selection_no = tract_selection_check(f"./mrtrix3_files/{pid}/rois")
            if tract_selection_no == 's':
                break
            tract_path = create_tract(tract_selection_no, first_flag, pid)
            tract_names.append(tract_path)
            additional_tract = input('Would you like additional tracts? (y/n): ')
            if additional_tract.lower() == 'n':
                break
        step += 1
        cont = input('Continue? (y/n): ')

    if step == 12 and cont.lower() == 'y':

        converted_nii_file = get_nii_file(pid)
        convert_tracts(converted_nii_file, 'debug', pid)
        step += 1
        cont = input('Continue? (y/n): ')

    if step == 13 and cont.lower() == 'y':
        base_file = get_nii_file(pid)
        while True:
            # Execute your registration function
            _, registered = registration('debug', dependencies, pid, base_file)
            file_paths["registered"].append(registered)
            # Ask the user if they want to continue
            choice = input("Would you like to register additional tracts? (y/n): ").strip().lower()
            # Check the input to decide whether to loop or exit
            if choice != 'y':
                print("Registration process complete.")
                break
        step += 1
        print()
        cont = input('Continue? (y/n): ')

    if step == 14 and cont.lower() == 'y':
        print()
        print("Creating objects step")
        print()


        converted_nii_file = get_nii_file(pid)
        correct_shape = get_shape(converted_nii_file)
        template_key = converted_nii_file.split('/')[-1].split('.')[0]
        templates_to_use = os.listdir(f"./mrtrix3_files/{pid}/template")
        for x in templates_to_use:
            if template_key in x:
                template_path = f"./mrtrix3_files/{pid}/template/template_{template_key}.dcm"

        "Select the template file you want to use if more than one is available"
        templates = {'t1_temp': None, 't2_temp': None}
        if 'flair' in template_path or 't2' in template_path:
            templates['t2_temp'] = f"./mrtrix3_files/{pid}/template/{x}"
        elif 't1' in template_path:
            templates['t1_temp'] = f"./mrtrix3_files/{pid}/template/{x}"

        for x in templates_to_use:
            if not templates['t2_temp']:
                if 'flair' in x and template_key not in x:
                    if get_shape(f"./mrtrix3_files/{pid}/template/{x}") == correct_shape:
                        templates['t2_temp'] = f"./mrtrix3_files/{pid}/template/{x}"
                elif 't2' in x and template_key not in x:
                    if get_shape(f"./mrtrix3_files/{pid}/template/{x}") == correct_shape:
                        templates['t2_temp'] = f"./mrtrix3_files/{pid}/template/{x}"
            if not templates['t1_temp']:
                if 't1' in x and template_key not in x:
                    if get_shape(f"./mrtrix3_files/{pid}/template/{x}") == correct_shape:
                        templates['t1_temp'] = f"./mrtrix3_files/{pid}/template/{x}"

        if templates['t1_temp'] and templates['t2_temp']:
            print('----------------------')
            print('There is both a t2 and a t1 template.  Do you want to use the:')
            print('1. t1 template')
            print('2. t2 template')
            template_check = input('Please input the option you want to use (1/2): ')
            if template_check == '1':
                template_file = templates["t1_temp"]
            else:
                template_file = templates["t2_temp"]
        else:
            template_file = template_path


        "Work horse of the actual dicom creation"
        current_dir = os.getcwd()
        nii_dir = f"{current_dir}/mrtrix3_files/{pid}/nifti/"
        overlay_dir = f"{current_dir}/mrtrix3_files/{pid}/overlays/"
        final_dir = f"{current_dir}/mrtrix3_files/{pid}/volumes/"

        relevant_dcm = pydicom.dcmread(template_file)
        data_dicom = relevant_dcm.pixel_array
        pixel_values_dicom = data_dicom.flatten()
        max_value = max(pixel_values_dicom)

        used_indices = set()

        while True:
            paths_to_convert = [p for p in os.listdir(nii_dir) if p.endswith('.nii.gz') and 'mrtrix3' in p]
            available_indices = [i for i in range(len(paths_to_convert)) if i not in used_indices]

            if not available_indices:
                print("No more tracts left to convert.")
                break

            print('Available tracts to convert to DICOMs:')
            for idx in available_indices:
                print(f"{idx + 1}. {paths_to_convert[idx]}")
            print()

            # Select tract
            select = input("Please type in the number of the tract you would like to convert:  ").strip()
            if not select.isdigit() or (int(select) - 1) not in available_indices:
                print("Invalid selection. Try again.\n")
                continue

            idx = int(select) - 1
            used_indices.add(idx)

            thresh_reg_tract = os.path.join(nii_dir, paths_to_convert[idx])
            file_paths["registered"].append(thresh_reg_tract)

            print(thresh_reg_tract)

            tract_name_pre = thresh_reg_tract.split('_NORM_registered')[0]
            tract_name = os.path.basename(tract_name_pre)

            # Define overlay output files
            burned = os.path.join(overlay_dir, f"{tract_name}_burned.nii.gz")
            burned_final = os.path.join(overlay_dir, f"{tract_name}_burned_final.nii.gz")
            binarised_object_hole = binarise_numpy(thresh_reg_tract, inv=True)
            binarised_object = binarise_numpy(thresh_reg_tract, inv=False)

            # Remove object
            nifti_img = nib.load(converted_nii_file)
            nifti_array = nifti_img.get_fdata()
            nifti_header = nifti_img.header
            nifti_affine = nifti_img.affine

            hole_array = binarised_object_hole * nifti_array

            base_max = np.max(nifti_array)
            burn_value = base_max + 250

            threshold_to_add = burn_value * binarised_object
            burned_array = hole_array + threshold_to_add
            burned_final_array = np.flip(burned_array, axis=1)

            mod_img = nib.Nifti1Image(burned_array, nifti_affine, nifti_header)
            mod_img_final = nib.Nifti1Image(burned_final_array, nifti_affine, nifti_header)
            nib.save(mod_img, burned)
            nib.save(mod_img_final, burned_final)

            # Inner loop for tuning DICOM
            object_path = os.path.join(final_dir, f"Brainlab_Object_{tract_name}.dcm")

            while True:
                print("\nDicom creation. Open the resultant dicom in Volumes and adjust if necessary.\n")

                create_brainlab_object(tract_name, burned_final, template_file, object_path)

                run(f"mrview {object_path}")
                check = input('Is the dicom file flipped? (y/n): ').strip().lower()
                if check == 'y':
                    create_brainlab_object(tract_name, burned, template_file, object_path)
                dataset = pydicom.dcmread(object_path)
                patient_no = dataset.PatientID
                if str(patient_no) in diff_data_dir.lower():
                    if not os.path.isdir(f"{diff_data_dir}/Processed/"):
                        copy_directory(f"{os.getcwd()}/mrtrix3_files/{pid}/", f"{diff_data_dir}/Processed/")
                    else:
                        safe_copy(f"{object_path}", f"{diff_data_dir}/Processed/mrtrix3_files/volumes")
                    break  # Done with DICOM tuning
                else:
                    break

            # Ask if user wants to process another
            print()
            happy_overall = input('Do you want to create another object? (y/n): ').strip().lower()
            print()
            if happy_overall == 'n':
                print("Finished.")
                break

main()