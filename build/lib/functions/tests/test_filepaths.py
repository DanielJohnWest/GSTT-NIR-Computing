from pathlib import Path
from functions.filepaths.get_files_as_list import get_files_as_list


def test_get_files_as_list_finds_all_files():
    test_dir = Path(__file__).parent / "resources" / "dummy_files"

    files = get_files_as_list(test_dir, '.mif')

    assert len(files) == 3
    assert all(f.suffix == ".mif" for f in files)
