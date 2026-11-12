def page(items: list, number: int, size: int) -> list:
    """Return page `number` (1-based) of `items`, `size` items per page.

    A page past the end is an empty list. number < 1 or size < 1 raises ValueError.
    """
    if number < 1 or size < 1:
        raise ValueError("number and size must be >= 1")
    start = (number - 1) * size
    return items[start:start + size]


def last(items: list, n: int) -> list:
    """Return the last `n` items of `items` (all of them if there are fewer).

    n == 0 gives []. n < 0 raises ValueError.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    return items[max(len(items) - n, 0):]
