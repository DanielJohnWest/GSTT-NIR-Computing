import re


def classify_spectroscopy_series(series_description):
    """
    Parameters
    ----------
    series_description : str or None
        The SeriesDescription tag value from a DICOM dataset.

    Returns
    -------
    dict or None
        {
            'kind': 'ecc' or 'ref',
            'base_name': str,            # series description with suffix removed
            'partner_description': str,  # SeriesDescription expected on the matching file
        }
        or None if the series description matches neither pattern.
    """
    if series_description is None:
        return None

    if re.search("_ECC", series_description):
        base_name = re.split("_ECC", series_description)[0]
        return {
            'kind': 'ecc',
            'base_name': base_name,
            'partner_description': base_name + '_ref',
        }

    if re.search("_ref", series_description):
        base_name = re.split("_ref", series_description)[0]
        return {
            'kind': 'ref',
            'base_name': base_name,
            'partner_description': base_name + '_ECC',
        }

    return None
