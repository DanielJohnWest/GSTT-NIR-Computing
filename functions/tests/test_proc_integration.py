
import os

import projects.Tarquin_Analysis.proc as proc


RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'resources', 'dummy_files')
ECC_PATH = os.path.join(RESOURCES_DIR, 'mrs_ECC.dcm')
REF_PATH = os.path.join(RESOURCES_DIR, 'mrs_ref.dcm')


def _bypass_institution_check(monkeypatch):
    monkeypatch.setattr(proc, 'is_evelina_spectroscopy', lambda ds: True)


def test_find_spec_pairs_ecc_and_ref_when_ecc_is_newest(monkeypatch):
    _bypass_institution_check(monkeypatch)

    runfilelist = [REF_PATH, ECC_PATH]  # ECC arrived last (newest)
    runfilelist, wsup_path, wref_path, ds = proc.find_spec(runfilelist)

    assert wsup_path == ECC_PATH
    assert wref_path == REF_PATH
    assert ds is not None
    assert runfilelist == []  # both files consumed from the tracking list


def test_find_spec_pairs_ecc_and_ref_when_ref_is_newest(monkeypatch):
    _bypass_institution_check(monkeypatch)

    runfilelist = [ECC_PATH, REF_PATH]  # ref arrived last (newest)
    runfilelist, wsup_path, wref_path, ds = proc.find_spec(runfilelist)

    assert wsup_path == ECC_PATH
    assert wref_path == REF_PATH
    assert ds is not None
    assert runfilelist == []


def test_find_spec_waits_when_partner_not_present_yet(monkeypatch):
    _bypass_institution_check(monkeypatch)

    runfilelist = [ECC_PATH]  # only the ECC file has arrived so far
    runfilelist, wsup_path, wref_path, ds = proc.find_spec(runfilelist)

    assert wsup_path is None
    assert wref_path is None
    assert ds is None
    assert runfilelist == [ECC_PATH]  # left in place to wait for its partner


def test_find_spec_rejects_pair_with_real_institution_check():
    # No monkeypatch here - proves the real (unpatched) institution check
    # correctly rejects this anonymized test data, as documented above.
    runfilelist = [REF_PATH, ECC_PATH]
    runfilelist, wsup_path, wref_path, ds = proc.find_spec(runfilelist)

    assert wsup_path is None
    assert ds is None
    # the newest file (ECC) gets popped off since it failed the institution check
    assert runfilelist == [REF_PATH]
