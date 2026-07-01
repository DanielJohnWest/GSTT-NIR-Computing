from functions.spectroscopy.is_evelina_spectroscopy import is_evelina_spectroscopy
from functions.spectroscopy.classify_spectroscopy_series import classify_spectroscopy_series
from functions.spectroscopy.find_matching_pair import find_matching_pair


class FakeDataset:
    """Minimal stand-in for a pydicom.Dataset for unit testing."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# --- is_evelina_spectroscopy -------------------------------------------------

def test_is_evelina_spectroscopy_true():
    ds = FakeDataset(InstitutionName='Evelina London Childrens Hospital')
    assert is_evelina_spectroscopy(ds) is True


def test_is_evelina_spectroscopy_false_other_institution():
    ds = FakeDataset(InstitutionName='Some Other Hospital')
    assert is_evelina_spectroscopy(ds) is False


def test_is_evelina_spectroscopy_missing_tag():
    ds = FakeDataset()
    assert is_evelina_spectroscopy(ds) is False


# --- classify_spectroscopy_series --------------------------------------------

def test_classify_ecc_series():
    result = classify_spectroscopy_series('svs_se_30_ECC')
    assert result['kind'] == 'ecc'
    assert result['base_name'] == 'svs_se_30'
    assert result['partner_description'] == 'svs_se_30_ref'


def test_classify_ref_series():
    result = classify_spectroscopy_series('svs_se_30_ref')
    assert result['kind'] == 'ref'
    assert result['base_name'] == 'svs_se_30'
    assert result['partner_description'] == 'svs_se_30_ECC'


def test_classify_unrelated_series():
    assert classify_spectroscopy_series('t1_mprage') is None


def test_classify_none_input():
    assert classify_spectroscopy_series(None) is None


# --- find_matching_pair -------------------------------------------------------

def test_find_matching_pair_found():
    candidates = [
        {'path': 'a.dcm', 'dataset': FakeDataset(SeriesDescription='svs_se_30_ref', StudyInstanceUID='1.2.3')},
        {'path': 'b.dcm', 'dataset': FakeDataset(SeriesDescription='t1_mprage', StudyInstanceUID='1.2.3')},
    ]
    match = find_matching_pair(candidates, 'svs_se_30_ref', '1.2.3')
    assert match['path'] == 'a.dcm'


def test_find_matching_pair_wrong_study_uid():
    candidates = [
        {'path': 'a.dcm', 'dataset': FakeDataset(SeriesDescription='svs_se_30_ref', StudyInstanceUID='9.9.9')},
    ]
    match = find_matching_pair(candidates, 'svs_se_30_ref', '1.2.3')
    assert match is None


def test_find_matching_pair_no_candidates():
    assert find_matching_pair([], 'svs_se_30_ref', '1.2.3') is None


def test_find_matching_pair_missing_tags_does_not_raise():
    candidates = [{'path': 'a.dcm', 'dataset': FakeDataset()}]
    match = find_matching_pair(candidates, 'svs_se_30_ref', '1.2.3')
    assert match is None
