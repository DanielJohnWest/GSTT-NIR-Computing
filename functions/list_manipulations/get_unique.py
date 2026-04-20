from typing import Any, List, Iterable

def get_unique(values: Iterable[Any]) -> List[Any]:
    """
    Return a list of unique values from the input, preserving original order.

    Args:
        values: An iterable (list, array, tuple, etc.) of values.

    Returns:
        A list containing only the unique values from the input,
        in the order they first appeared.

    Examples:
        >>> get_unique([1, 2, 2, 3, 1, 4])
        [1, 2, 3, 4]
        >>> get_unique(['a', 'b', 'a', 'c'])
        ['a', 'b', 'c']
    """

    seen: set = set()
    result: List[Any] = []

    for item in values:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result
