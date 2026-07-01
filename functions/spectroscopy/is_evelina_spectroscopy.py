import re


def is_evelina_spectroscopy(ds):
    """
    Parameters
    ----------
    ds : pydicom.Dataset
        An already-loaded DICOM dataset.

    Returns
    -------
    bool
        True if InstitutionName contains 'Evelina', False otherwise
        (including when the tag is missing).
    """
    institution_name = getattr(ds, 'InstitutionName', None)
    if institution_name is None:
        return False

    return re.search("Evelina", institution_name) is not None
