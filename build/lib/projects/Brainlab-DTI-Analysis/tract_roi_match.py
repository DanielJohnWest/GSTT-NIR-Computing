from tabulate import tabulate

def roi_table():
    tracts = [
        ["Arcuate Fasciculus", "AF_[X]", "BROCA_[X]", "SLF_[X]", "AF_exclude", ""],
        ["CST Motor Hand", "[X]HandM1", "[X]-Ped", "[X]-Cap", "", ""],
        ["CST Sensory Hand/Foot", "[X]handS1", "[X]-Thal", "", "", "-stop so the tract stops at the thalamus"],
        ["Optic Radiation", "[X]-LGN", "[X]-latCalc", "[X]-latVentr", "OR_exclude", ""],
        ["CST Sensory/Motor Foot", "[X]FootM1", "[X]-Ped", "[X]-Cap", "", ""],
        ["CST Motor Lip/Face", "[X]FaceM1", "[X]-Ped", "[X]-Cap", "", ""],
    ]

    headers = ["Tract name", "Seed", "Include", "Include", "Exclude (optional)", "Other"]

    print(tabulate(tracts, headers=headers, tablefmt="grid"))
