import os

# Define the required ROIs for each tract
TRACTS = {
    "1": {"name": "AF: Arcuate Fasciculus", "seed": ["AF_L", "AF_R"],
          "includes": {"AF_L": ["SLF_L", "BROCA_L"], "AF_R": ["SLF_R", "BROCA_R"]}},
    "2": {"name": "MHA: Corticospinal Tract Hand", "seed": ["RHandM1", "LHandM1"],
          "includes": {"RHandM1": ["L-Ped", "L-Cap"], "LHandM1": ["R-Ped", "R-Cap"]}},
    "3": {"name": "SHA: Sensory Hand Area", "seed": ["RHandS1", "LHandS1"],
          "includes": {"RHandS1": ["L-Thal"], "LHandS1": ["R-Thal"]}},
    "4": {"name": "Lip Motor Area CST", "seed": ["LipM1"],
          "includes": {"LipM1_R": ["L-Ped", "L-Cap"], "LipM1_L": ["R-Ped", "R-Cap"]}},
    "5": {"name": "Lip Sensory Area CST", "seed": ["LipS1"],
          "includes": {"LipS1_R": ["L-Ped", "L-Cap"], "LipS1_L": ["R-Ped", "R-Cap"]}},
    "6": {"name": "Foot Motor Area CST", "seed": ["RFootM1", "LFootM1"],
          "includes": {"RFootM1": ["L-Ped", "L-Cap"], "LFootM1": ["R-Ped", "R-Cap"]}},
    "7": {"name": "Optic Radiation", "seed": ["L-LGN", "R-LGN"],
          "includes": {"L-LGN": ["L-latCalc", "L-latVentr"], "R-LGN": ["R-latCalc", "R-latVentr"]}},
    "8": {"name": "Sensory Foot CST", "seed": ["RFootS1", "LFootS1"],
          "includes": {"RFootS1": ["L-Thal"], "LFootS1": ["R-Thal"]}},
    "9": {"name": "MFace CST", "seed": ["RFaceM1", "LFaceM1"],
          "includes": {"RFaceM1": ["L-Ped", "L-Cap"], "LFaceM1": ["R-Ped", "R-Cap"]}}
}

def tract_selection_check(roi_dir):
    """
    Interactive tract selection. Tells the user if sufficient ROIs exist to generate each tract.
    Dynamically updates ROI files if they are added/removed during runtime.
    Uses exact filename matches, except allows _L/_R flexibility for seeds like LipM1.
    """
    while True:
        # Refresh ROI files each loop iteration
        roi_files = [f.split(".")[0] for f in os.listdir(roi_dir) if f.endswith(".mif")]

        print("\nWhich tract do you want to check?")
        for key, info in sorted(TRACTS.items()):
            print(f"({key}) {info['name']}")
        print("(c) Custom")
        print("(s) Skip \n")

        choice = input("Enter your choice: ").strip().lower()
        if choice == "s":
            return 's'
        if choice == "c":
            return 'c'
        if choice not in TRACTS:
            print("Invalid choice. Try again.")
            continue

        tract = TRACTS[choice]
        print(f"\nChecking tract: {tract['name']}")

        valid_seeds = []  # seeds that can be used to generate this tract
        partial_seeds = []  # seeds that exist but are missing includes
        missing_seeds = []  # seeds not found at all

        for seed in tract["seed"]:
            # Handle flexible seeds (LipM1, LipS1, etc.)
            if seed in roi_files:
                actual_seed = seed
            elif f"{seed}_L" in roi_files:
                actual_seed = f"{seed}_L"
            elif f"{seed}_R" in roi_files:
                actual_seed = f"{seed}_R"
            else:
                missing_seeds.append(seed)
                continue

            # Check includes
            includes_needed = tract["includes"].get(actual_seed, [])
            missing_rois = [inc for inc in includes_needed if inc not in roi_files]

            if not missing_rois:
                print(f"- Tract with seed '{actual_seed}' can be generated ✅")
                valid_seeds.append(actual_seed)
            else:
                print(f"- Tract with seed '{actual_seed}' is missing ROIs ❌: {', '.join(missing_rois)}")
                partial_seeds.append((actual_seed, missing_rois))

        # Decide outcome after checking all seeds
        if valid_seeds:
            # If at least one seed works, allow tract
            return choice
        else:
            print("\nSummary:")
            if missing_seeds:
                print(f"  Missing seeds ❌: {', '.join(missing_seeds)}")
            if partial_seeds:
                for seed, missing in partial_seeds:
                    print(f"  Seed {seed} missing ROIs: {', '.join(missing)}")

            print()
            print('--------------------------------------------------')
            print("Option 1: Create the correct ROIs (will return to tract selection).")
            print("Option 2: Enter a custom tract. These are individual commands, so proceed with caution.")
            print()
            select = input("Enter which option : ").strip().lower()
            if select == "2":
                return 'c'
            else:
                continue  # go back to main menu
