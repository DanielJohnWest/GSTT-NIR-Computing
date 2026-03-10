import os
import pydicom
from pathlib import Path
from pydicom.uid import generate_uid
from functions.dicoms.anonymise_dicom import anonymise_dicom


def test_anonymise_dicom():
    test_dir = Path(__file__).parent / "resources" / "dummy_files"
    input_dcm = f"{test_dir}/test.dcm"

    anon_path = anonymise_dicom(input_dcm, test_dir)
    ds = pydicom.dcmread(anon_path)

    assert ds.PatientID == ""

    Path(anon_path).unlink(missing_ok=True)