```python
def cache_key(params: dict) -> tuple:
    pairs = []
    for name in sorted(params):
        value = params[name]
        if isinstance(value, list):
            value = tuple(value)
        pairs.append((name, value))
    return tuple(pairs)
```

**Why it works**

- A dict can't be a dict key (it's mutable, so unhashable). A tuple of hashable values can. So the key is a tuple of `(name, value)` pairs.
- `sorted(params)` iterates the names in sorted order, so `{"a": 1, "b": 2}` and `{"b": 2, "a": 1}` produce the same tuple. Without sorting, insertion order would leak into the key and you'd get cache misses for the same request.
- A list value would make the whole tuple unhashable: `(("tags", ["go"]),)` is a tuple containing a list (lesson section 6). `tuple(value)` builds a new, hashable tuple with the same items.
- `value = tuple(value)` rebinds the local name `value`. It never touches `params`. Writing `params[name] = tuple(value)` instead would also pass most tests, but it changes the caller's dict, and `test_params_are_not_changed` catches it.
- `pairs` is a list while you build it (lists are cheap to append to), then `tuple(pairs)` freezes it.

**Alternatives**

- `tuple(sorted(...))` over a generator expression gives the same thing in one line (comprehensions come in PY.M03).
- `frozenset(params.items())` is hashable and order-independent, but it only works when no value is a list, and it loses the readable sorted order.
- Real caches often use `json.dumps(params, sort_keys=True)` as a string key. That also handles nested dicts.

**Limit:** values nested deeper (a list of lists, a dict value) would still be unhashable. That needs a recursive version.
