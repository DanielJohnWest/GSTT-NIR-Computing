def add_list(myList):
    """
    This function takes a list of numbers and returns the sum of all the numbers in the list.

    Parameters:
    myList (list): A list of numbers.

    Returns:
    int: The sum of all the numbers in the list.
    """
    total = 0
    for num in myList:
        total += num
    return total