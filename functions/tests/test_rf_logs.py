from pathlib import Path
from functions.rf_logs.extract_protocol_times import extract_protocol_times


def test_extract_protocol_times_gets_correct_times():
    test_dir = Path(__file__).parent / "resources" / "dummy_files"

    sequence_data = extract_protocol_times(test_dir, keep_locs_and_adjs=True)
    lengths = []
    for i in sequence_data:
        lengths.append(len(sequence_data[i]))
    assert len(sequence_data) == 2
    assert sum(lengths) == 73
