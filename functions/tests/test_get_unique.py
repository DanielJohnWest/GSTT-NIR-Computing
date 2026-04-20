from functions.list_manipulations.get_unique import get_unique

def test_get_unique():
    assert get_unique([1, 2, 2, 3, 1, 4]) == [1, 2, 3, 4]
    assert get_unique(['a', 'b', 'a', 'c']) == ['a', 'b', 'c']
