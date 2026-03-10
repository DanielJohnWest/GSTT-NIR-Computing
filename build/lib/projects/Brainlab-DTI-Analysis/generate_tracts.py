import os
import subprocess
from functions import run

def get_tract_path(command_parts):
    tract_path = None
    for i in command_parts:
        if '.tck' in i:
            tract_path = i.strip()
    return tract_path

def finish_check():
    check = input('Are you happy with the tract? (y/n):  ')
    return check

def display_tract(tract_path, pid):
    """Display the generated tract in mrview."""
    white_matter = f"{os.getcwd()}/mrtrix3_files/{pid}/fods/wm_fod.mif"
    print(f"Displaying tract: {tract_path}")
    run(f"mrview -mode 2 -load {white_matter} -interpolation 0 -tractography.load {tract_path}")

def tract_run(pid, command_parts, seed=None, includes=None, excludes=None, notes=None):
    subprocess.run(command_parts)
    tract_path = get_tract_path(command_parts)
    display_tract(tract_path, pid)
    check = finish_check()
    return tract_path, check

def confirm_and_run(pid, command_parts, seed=None, includes=None, excludes=None, notes=None):
    """
    Show tractography parameters before running and allow editing.
    Handles seeds, includes, excludes, and general tckgen options.
    """
    # Extract common flags (if present)
    cutoff = None
    angle = None
    step = None
    select = None
    for i, part in enumerate(command_parts):
        if part == "-cutoff":
            cutoff = command_parts[i+1]
        if part == "-angle":
            angle = command_parts[i+1]
        if part == "-step":
            step = command_parts[i+1]
        if part == "-select":
            select = command_parts[i+1]

    print("\n===== TRACTOGRAPHY PARAMETERS =====")
    print(f"Seed ROI: {seed if seed else 'None'}")
    print(f"Include ROIs: {includes if includes else 'None'}")
    print(f"Exclude ROIs: {excludes if excludes else 'None'}")
    print(f"Cutoff: {cutoff if cutoff else '(default)'}")
    print(f"Angle: {angle if angle else '(default)'}")
    print(f"Step: {step if step else '(default)'}")
    print(f"Select: {select if select else 'None'}")
    print("===================================\n")

    # --- Ask if user wants to change include/exclude regions ---
    choice_rois = input("Do you want to modify include/exclude ROIs? (y/n): ").strip().lower()
    if choice_rois == "y":
        new_includes = input(f"Include ROIs [{includes if includes else 'None'}]: ").strip()
        new_excludes = input(f"Exclude ROIs [{excludes if excludes else 'None'}]: ").strip()
        includes = new_includes if new_includes else includes
        excludes = new_excludes if new_excludes else excludes
        print(f"\nUpdated Include ROIs: {includes if includes else 'None'}")
        print(f"Updated Exclude ROIs: {excludes if excludes else 'None'}\n")

    # --- Ask if user wants to change cutoff/angle/step/select ---
    choice_params = input("Do you want to modify tckgen parameters (cutoff/angle/step/select)? (y/n): ").strip().lower()
    if choice_params == "y":
        new_cutoff = input(f"Cutoff [{cutoff if cutoff else 'default'}]: ").strip() or cutoff
        new_angle = input(f"Angle [{angle if angle else 'default'}]: ").strip() or angle
        new_step = input(f"Step size [{step if step else 'default'}]: ").strip() or step
        new_select = input(f"Select [{select if select else 'None'}]: ").strip() or select
    else:
        new_cutoff, new_angle, new_step, new_select = cutoff, angle, step, select

    # --- Defaults for extras so they're always defined ---
    add_force = False
    add_seed_uni = False

    # --- Ask if user wants to add extra flags ---
    choice_extras = input("Do you want to add a -force or -seed_unidirectional argument? (y/n): ").strip().lower()
    if choice_extras == "y":
        add_force = input("Add -force? (y/n): ").strip().lower() == "y"
        add_seed_uni = input("Add -seed_unidirectional? (y/n): ").strip().lower() == "y"

    # Update command list
    cmd = command_parts[:]

    # Update standard params
    if new_cutoff:
        if "-cutoff" in cmd:
            cmd[cmd.index("-cutoff")+1] = new_cutoff
        else:
            cmd.extend(["-cutoff", new_cutoff])
    if new_angle:
        if "-angle" in cmd:
            cmd[cmd.index("-angle")+1] = new_angle
        else:
            cmd.extend(["-angle", new_angle])
    if new_step:
        if "-step" in cmd:
            cmd[cmd.index("-step")+1] = new_step
        else:
            cmd.extend(["-step", new_step])
    if new_select:
        if "-select" in cmd:
            cmd[cmd.index("-select")+1] = new_select
        else:
            cmd.extend(["-select", new_select])

    # Handle -seed_unidirectional
    if add_seed_uni:
        if "-seed_unidirectional" not in cmd:  # avoid duplicates
            if "-force" in cmd:
                force_index = cmd.index("-force")
                cmd.insert(force_index, "-seed_unidirectional")
            else:
                cmd.append("-seed_unidirectional")

    # Handle -force
    if add_force and "-force" not in cmd:
        cmd.append("-force")

    command_parts = cmd
    if new_select:
        for idx, i in enumerate(command_parts):
            if '.tck' in i:
                i = f"{i.split('.')[0]}_{new_select}.tck"
                command_parts[idx] = i
    print("\nUpdated command:")
    print(" ".join(command_parts))
    input("Press Enter to run with updated parameters...")

    subprocess.run(command_parts)
    tract_path = get_tract_path(command_parts)
    display_tract(tract_path, pid)
    check = finish_check()
    return tract_path, check


def run_tract_generation(pid, choice, first_flag, finished_flag):

    dispatch = {
        "default": tract_run,
        "special": confirm_and_run
    }
    choice = choice.strip()

    if first_flag:
        flag = "default"
    else:
        flag = "special"

    if choice == "1":
        print("Running AF tract...")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/AF_L.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-AF_L.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/AF_L.mif",
                "-include", f"mrtrix3_files/{pid}/rois/SLF_L.mif",
                "-include", f"mrtrix3_files/{pid}/rois/BROCA_L.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.05", "-select", "1000", "-force"
            ], seed="AF_L", includes=["SLF_L", "BROCA_L"], notes="AF Left hemisphere")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/AF_R.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-AF_R.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/AF_R.mif",
                "-include", f"mrtrix3_files/{pid}/rois/SLF_R.mif",
                "-include", f"mrtrix3_files/{pid}/rois/BROCA_R.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.05", "-select", "1000", "-force"
            ], seed="AF_R", includes=["SLF_R", "BROCA_R"], notes="AF Right hemisphere")
        return tract_path, check

    elif choice == "2":
        print("Running MHA tract...")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/RHandM1.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-RH_MHA.tck",
                "-include", f"mrtrix3_files/{pid}/rois/L-Ped.mif",
                "-seed_image", f"mrtrix3_files/{pid}/rois/RHandM1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-Cap.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.05", "-force"
            ], seed="RHandM1", includes=["L-Ped", "L-Cap"], notes="Motor Hand CST Right")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/LHandM1.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-LH_MHA.tck",
                "-include", f"mrtrix3_files/{pid}/rois/R-Ped.mif",
                "-seed_image", f"mrtrix3_files/{pid}/rois/LHandM1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-Cap.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.05", "-seed_unidirectional", "-force"
            ], seed="LHandM1", includes=["R-Ped", "R-Cap"], notes="Motor Hand CST Left")
        return tract_path, check

    elif choice == "3":
        print("Running Sensory Hand Area tract...")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/RHandS1.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-R-SHA.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/RHandS1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-Thal.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.1", "-force"
            ], seed="RHandS1", includes=["L-Thal"], notes="Sensory Hand CST Right")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/LHandS1.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-L-SHA.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/LHandS1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-Thal.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.1", "-force"
            ], seed="LHandS1", includes=["R-Thal"], notes="Sensory Hand CST Left")
        return tract_path, check

    elif choice == "4":
        print("Running Lip Motor CST...")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/LipM1.mif") and os.path.isfile(f"mrtrix3_files/{pid}/rois/L-Cap.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-R-Lip.tck",
                "-include", f"mrtrix3_files/{pid}/rois/L-Ped.mif",
                "-seed_image", f"mrtrix3_files/{pid}/rois/LipM1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-Cap.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.1", "-seed_unidirectional", "-force"
            ], seed="LipM1", includes=["L-Ped", "L-Cap"], notes="Lip Motor CST Right")

        if os.path.isfile(f"mrtrix3_files/{pid}/rois/LipM1.mif") and os.path.isfile(f"mrtrix3_files/{pid}/rois/R-Cap.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-L-Lip.tck",
                "-include", f"mrtrix3_files/{pid}/rois/R-Ped.mif",
                "-seed_image", f"mrtrix3_files/{pid}/rois/LipM1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-Cap.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.1", "-seed_unidirectional", "-force"
            ], seed="LipM1", includes=["R-Ped", "R-Cap"], notes="Lip Motor CST Left")
        return tract_path, check

    elif choice == "5":
        print("Running Lip Sensory CST...")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/LipS1.mif") and os.path.isfile(f"mrtrix3_files/{pid}/rois/L-Cap.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-R-LipSens.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/LipS1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-Ped.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-Cap.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.1", "-seed_unidirectional", "-force"
            ], seed="LipS1", includes=["L-Ped", "L-Cap"], notes="Lip Sensory CST Right")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/LipM1.mif") and os.path.isfile(f"mrtrix3_files/{pid}/rois/R-Cap.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-L-LipSens.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/LipS1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-Ped.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-Cap.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.1", "-seed_unidirectional", "-force"
            ], seed="LipS1", includes=["R-Ped", "R-Cap"], notes="Lip Sensory CST Left")
        return tract_path, check

    elif choice == "6":
        print("Running Foot Motor CST...")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/RFootM1.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-RF_MFO.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/RFootM1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-Ped.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-Cap.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.1", "-seed_unidirectional", "-force"
            ], seed="RFootM1", includes=["L-Ped", "L-Cap"], notes="Foot Motor CST Right")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/LFootM1.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-LF_MFO.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/LFootM1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-Ped.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-Cap.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.1", "-seed_unidirectional", "-force"
            ], seed="LFootM1", includes=["R-Ped", "R-Cap"], notes="Foot Motor CST Left")
        return tract_path, check

    elif choice == "7":
        print("Running Optic Radiation...")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/L-LGN.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-L-OR_UNI.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/L-LGN.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-latCalc.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-latVentr.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.05", "-seed_unidirectional"
            ], seed="L-LGN", includes=["L-latCalc", "L-latVentr"], notes="Optic Radiation Left")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/R-LGN.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-R-OR_UNI.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/R-LGN.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-latCalc.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-latVentr.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.05", "-seed_unidirectional"
            ], seed="R-LGN", includes=["R-latCalc", "R-latVentr"], notes="Optic Radiation Right")
        return tract_path, check

    elif choice == "8":
        print("Running Sensory Foot CST...")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/RFootS1.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-R-SFO.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/RFootS1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-Thal.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.1"
            ], seed="RFootS1", includes=["L-Thal"], notes="Sensory Foot CST Right")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/LFootS1.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-L-SFO.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/LFootS1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-Thal.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.1"
            ], seed="LFootS1", includes=["R-Thal"], notes="Sensory Foot CST Left")
        return tract_path, check

    elif choice.lower() == "9":
        print("Running MFace CST...")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/RFaceM1.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", f"mrtrix3_files/{pid}/tracts/mrtrix3-R_MFace.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/RFaceM1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-Ped.mif",
                "-include", f"mrtrix3_files/{pid}/rois/L-Cap.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.05", "-select", "1000", "-force"
            ], seed="RFaceM1", includes=["L-Ped", "L-Cap"], notes="Motor Face CST Right")
        if os.path.isfile(f"mrtrix3_files/{pid}/rois/LFaceM1.mif"):
            tract_path, check = dispatch[flag](pid, [
                "tckgen", f"mrtrix3_files/{pid}/fods/wm_fod.mif", "mrtrix3_files/tracts/mrtrix3-L_MFace.tck",
                "-seed_image", f"mrtrix3_files/{pid}/rois/LFaceM1.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-Ped.mif",
                "-include", f"mrtrix3_files/{pid}/rois/R-Cap.mif",
                "-step", "1", "-angle", "45", "-cutoff", "0.05", "-select", "1000", "-force"
            ], seed="LFaceM1", includes=["R-Ped", "R-Cap"], notes="Motor Face CST Left")
        return tract_path, check

    elif choice.lower() == "c":
        print('---------------------------')
        print('Preparing for custom tracts.')
        print()

        cmd = input('Please type the command you want to run:  ')
        run(cmd)
        a = cmd.split(' ')
        tract_output = [element for element in a if '.tck' in element][0]
        display_tract(tract_output, pid)
        check = finish_check()

        print(tract_output, check)

        return tract_output, check

    elif choice.lower() == "s":
        print("Skipping...")

    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    run_tract_generation()
