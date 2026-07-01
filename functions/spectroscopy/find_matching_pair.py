def find_matching_pair(candidates, target_series_description, target_study_uid):
    """
    Parameters
    ----------
    candidates : list of dict
        Each dict must have keys 'path' (str) and 'dataset' (pydicom.Dataset
        or any object with SeriesDescription / StudyInstanceUID attributes).
    target_series_description : str
        The SeriesDescription we're looking for in a candidate.
    target_study_uid : str
        The StudyInstanceUID that must also match.

    Returns
    -------
    dict or None
        The matching candidate dict ({'path', 'dataset'}), or None if no
        match is found.
    """
    for candidate in candidates:
        ds = candidate['dataset']
        series_description = getattr(ds, 'SeriesDescription', 'no compare SD')
        study_uid = getattr(ds, 'StudyInstanceUID', 'no compare UID')

        if series_description == target_series_description and study_uid == target_study_uid:
            return candidate

    return None
