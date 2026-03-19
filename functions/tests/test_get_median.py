from functions.list_manipulations.get_median import get_median

def test_get_median():
    assert get_median([1, 2, 3]) == 2
    assert get_median([1, 2, 3, 4]) == 2.5
    assert get_median([5, 3, 1, 4, 2]) == 3
    assert get_median([5, 3, 1, 4]) == 3.5
    assert get_median([1]) == 1
