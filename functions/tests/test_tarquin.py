from unittest.mock import patch

from functions.tarquin.escape_filepath import escape_filepath
from functions.tarquin.build_tarquin_command import build_tarquin_command
from functions.tarquin.run_tarquin import run_tarquin


# --- escape_filepath -----------------------------------------------------

def test_escape_filepath_spaces():
    assert escape_filepath('my file.dcm') == r'my\ file.dcm'


def test_escape_filepath_dashes():
    # Confirms re.sub(r"\-", r"\-", ...) is NOT a no-op: it inserts a
    # literal escaping backslash before each dash.
    assert escape_filepath('my-file.dcm') == r'my\-file.dcm'


def test_escape_filepath_no_special_characters():
    assert escape_filepath('plainfile.dcm') == 'plainfile.dcm'


# --- build_tarquin_command ------------------------------------------------

def test_build_tarquin_command_default_output():
    command = build_tarquin_command('wsup.dcm', 'wref.dcm')
    assert command == 'tarquin --input wsup.dcm --input_w wref.dcm --output_pdf temp.pdf'


def test_build_tarquin_command_custom_output():
    command = build_tarquin_command('wsup.dcm', 'wref.dcm', output_pdf='out.pdf')
    assert command == 'tarquin --input wsup.dcm --input_w wref.dcm --output_pdf out.pdf'


# --- run_tarquin (subprocess mocked, no real tarquin install needed) ------

@patch('functions.tarquin.run_tarquin.subprocess.call')
def test_run_tarquin_calls_subprocess_with_built_command(mock_call):
    mock_call.return_value = 0
    result = run_tarquin('wsup.dcm', 'wref.dcm')

    expected_command = 'tarquin --input wsup.dcm --input_w wref.dcm --output_pdf temp.pdf'
    mock_call.assert_called_once_with(expected_command, shell=True)
    assert result == 0
