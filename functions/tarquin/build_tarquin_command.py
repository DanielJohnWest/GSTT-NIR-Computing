"""
build_tarquin_command
------------------------
Builds the shell command string used to run tarquin on a matched pair of
ECC (water-suppressed) and ref (water-reference) files.

Pure function - string building only, no subprocess execution, so it needs
no tarquin installation to test.
"""


def build_tarquin_command(wsup_path, wref_path, output_pdf='temp.pdf'):
    """
    Parameters
    ----------
    wsup_path : str
        Escaped path to the water-suppressed (_ECC) file.
    wref_path : str
        Escaped path to the water-reference (_ref) file.
    output_pdf : str, default 'temp.pdf'
        Output PDF filename tarquin should write to.

    Returns
    -------
    str
        The full tarquin command string.
    """
    return (
        'tarquin --input ' + wsup_path +
        ' --input_w ' + wref_path +
        ' --output_pdf ' + output_pdf
    )
