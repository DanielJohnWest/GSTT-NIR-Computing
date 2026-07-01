r"""
escape_filepath
-----------------
Escapes a single filepath string for safe use in a shell command passed to
tarquin (whitespace and dashes).

This reproduces the original wsrfix() from proc.py, split so a single
filepath can be escaped and tested directly. Note for anyone re-reading
the original: `re.sub(r"\-", r"\-", ...)` looks like a no-op at a glance,
but in Python's re.sub, an unrecognized backslash-escape in the
*replacement* string (here `\-`) is treated as a literal backslash
followed by that character - so it does correctly insert an escaping
backslash before each dash. Verified with a direct check rather than
assumed - see functions/tests/test_tarquin.py.
"""

import re


def escape_filepath(path):
    """
    Parameters
    ----------
    path : str
        A raw filepath that may contain spaces or dashes.

    Returns
    -------
    str
        The escaped filepath, with spaces and dashes backslash-escaped.
    """
    escaped = re.sub(r"\s", r"\ ", path)
    escaped = re.sub(r"\-", r"\-", escaped)
    return escaped
