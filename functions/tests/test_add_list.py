from functions.list_manipulations.add_list import add_list

def test_add_list():
    assert add_list([1, 2, 3]) == 6
    assert add_list([1, 2, 3, 4]) == 10
    assert add_list([5, 3, 1, 4, 2]) == 15
    assert add_list([5, 3, 1, 4]) == 13
    assert add_list([1]) == 1