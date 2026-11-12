def cache_key(params: dict) -> tuple:
    """Turn query parameters into a hashable cache key.

    The key is a tuple of (name, value) pairs sorted by name. List values become
    tuples. Two dicts with the same contents give equal keys, whatever their order.
    `params` itself must not be changed.

    cache_key({"page": 2, "tags": ["go", "py"]}) == (("page", 2), ("tags", ("go", "py")))
    """
    raise NotImplementedError
