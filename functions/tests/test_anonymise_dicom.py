import collections
import pydicom
from pathlib import Path
from functions.dicoms.anonymise_dicom import anonymise_dicom

DUMMY_DIR = Path(__file__).parent / "resources" / "dummy_files"


def test_anonymise_dicom_single_file(tmp_path, monkeypatch):
    prompts = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "Pseudo 01")
    input_dcm = DUMMY_DIR / "test.dcm"
    original = pydicom.dcmread(input_dcm)

    outputs = anonymise_dicom(str(input_dcm), str(tmp_path))

    assert prompts == ["Insert pseudonym: "]
    assert len(outputs) == 1
    ds = pydicom.dcmread(outputs[0])
    assert Path(outputs[0]).name == f"{ds.SOPInstanceUID}.dcm"
    assert ds.PatientName == "Pseudo 01"
    assert ds.PatientID == "Pseudo 01"

    # No original identifier survives anywhere in the file, including inside sequences
    raw = Path(outputs[0]).read_bytes()
    for keyword in ["PatientBirthDate", "AccessionNumber", "InstitutionName", "StationName",
                    "DeviceSerialNumber", "StudyDate", "StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID"]:
        assert str(original[keyword].value).encode() not in raw, keyword
    for name in [original.PatientName, original.ReferringPhysicianName]:
        assert str(name.family_name).encode() not in raw
    assert str(original.PatientID).encode() not in raw
    assert "PatientAge" not in ds
    assert not any(elem.tag.is_private for elem in ds.iterall())

    assert ds.file_meta.MediaStorageSOPInstanceUID == ds.SOPInstanceUID
    assert ds.PatientIdentityRemoved == "YES"
    assert ds.LongitudinalTemporalInformationModified == "REMOVED"
    assert ds.DeidentificationMethodCodeSequence[0].CodeValue == "113100"
    assert ds.PixelData == original.PixelData


def test_anonymise_dicom_blank_pseudonym_skips_non_dicom(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")

    outputs = anonymise_dicom(str(DUMMY_DIR / "dcm_test"), str(tmp_path))

    # test.txt is skipped, test_nest.dcm is anonymised
    assert len(outputs) == 1
    assert list(tmp_path.iterdir()) == [Path(outputs[0])]
    ds = pydicom.dcmread(outputs[0])
    assert ds.PatientName == "Anonymous"
    assert ds.PatientID == "Anonymous"


def test_anonymise_dicom_folder_keeps_series_grouping(tmp_path):
    input_dir = DUMMY_DIR / "non_dcm_test"
    original_paths = [p for p in sorted(input_dir.rglob("*")) if p.is_file() and p.name != ".DS_Store"]
    originals = [pydicom.dcmread(p, stop_before_pixels=True) for p in original_paths]

    outputs = anonymise_dicom(str(input_dir), str(tmp_path), pseudonym="Pseudo 02")
    anonymised = [pydicom.dcmread(p, stop_before_pixels=True) for p in outputs]

    assert len(anonymised) == len(originals) == 130
    assert all(ds.PatientName == "Pseudo 02" for ds in anonymised)

    # UIDs are all new, but files from the same study/series still share them
    new_series = collections.Counter(ds.SeriesInstanceUID for ds in anonymised)
    old_series = collections.Counter(ds.SeriesInstanceUID for ds in originals)
    assert sorted(new_series.values()) == sorted(old_series.values())
    assert not set(new_series) & set(old_series)
    assert len({ds.StudyInstanceUID for ds in anonymised}) == 1
    assert {ds.StudyInstanceUID for ds in anonymised} != {ds.StudyInstanceUID for ds in originals}

    # Originals are untouched
    assert pydicom.dcmread(original_paths[0]).PatientName == "Mr Test"
