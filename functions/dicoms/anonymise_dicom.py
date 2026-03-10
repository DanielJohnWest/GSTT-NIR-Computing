import os
import pydicom
from pydicom.uid import generate_uid

def anonymise_dicom(input_dicom_path, output_dir):

    """
    Anonymise a DICOM file by removing common patient-identifying fields.

    Parameters
    ----------
    input_dicom_path : str
        Path to input DICOM file
    output_dir : str
        Directory where anonymised DICOM will be saved

    Returns
    -------
    str
        Path to saved anonymised DICOM file
    """
    print(input_dicom_path)
    ds = pydicom.dcmread(input_dicom_path)

    # Fields commonly containing patient identifiers
    fields_to_blank = [
        "PatientName",
        "PatientID",
        "PatientBirthDate",
        "PatientSex",
        "PatientAddress",
        "PatientTelephoneNumbers",
        "PatientMotherBirthName",
        "OtherPatientIDs",
        "OtherPatientNames",
        "EthnicGroup",
        "InstitutionName",
        "InstitutionAddress",
        "ReferringPhysicianName",
        "PerformingPhysicianName",
        "OperatorsName",
        "StudyID",
        "AccessionNumber"
    ]

    for field in fields_to_blank:
        if field in ds:
            ds.data_element(field).value = ""

    # Replace UIDs with new ones
    uid_fields = [
        "StudyInstanceUID",
        "SeriesInstanceUID",
        "SOPInstanceUID"
    ]

    for field in uid_fields:
        if field in ds:
            ds.data_element(field).value = generate_uid()

    # Remove private tags (often contain hidden identifiers)
    ds.remove_private_tags()

    # Optional: mark as anonymized
    ds.PatientIdentityRemoved = "YES"
    ds.DeidentificationMethod = "Basic Python pydicom anonymisation"

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{input_dicom_path.split('/')[-1].split('.')[0]}_anon.dcm")
    print(output_path)
    ds.save_as(output_path)

    return output_path