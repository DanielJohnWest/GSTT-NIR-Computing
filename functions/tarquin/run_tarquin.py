"""
run_tarquin
-------------
Thin wrapper that actually executes tarquin as a subprocess. Kept
intentionally minimal since it's an I/O boundary (needs a real tarquin
install to actually run); the command string itself is built and tested
separately in build_tarquin_command(), and this wrapper is tested with
subprocess.call mocked out.
"""

import subprocess

from functions.tarquin.build_tarquin_command import build_tarquin_command


def run_tarquin(wsup_path, wref_path, output_pdf='temp.pdf'):
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
    int
        The subprocess return code (0 on success).
    """
    command = build_tarquin_command(wsup_path, wref_path, output_pdf)
    print(command)
    return subprocess.call(command, shell=True)
