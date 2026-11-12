```python
def page(items: list, number: int, size: int) -> list:
    if number < 1 or size < 1:
        raise ValueError("number and size must be >= 1")
    start = (number - 1) * size
    return items[start:start + size]


def last(items: list, n: int) -> list:
    if n < 0:
        raise ValueError("n must be >= 0")
    return items[max(len(items) - n, 0):]
```

**Why it works**

- **`page` needs no "past the end" check.** For page 4 of 7 items with size 3, the slice is `items[9:12]`. Both bounds are greater than `len(items)`, so both clamp to 7, and `7:7` is `[]`. The last partial page, `items[6:9]`, clamps its end to 7 and returns `['e7']`. In Go, `s[9:12]` would panic, so you'd need `min(start, len(s))` on both bounds.
- **Validation is still yours.** Clamping makes the slice safe, but `page(items, 0, 3)` would compute `start = -3`, and a negative start counts from the end: you'd silently get the last 3 items. Invalid input must fail loudly at the boundary.
- **`last` avoids the `-0` trap.** `items[-n:]` returns the whole list when `n == 0`. Computing the start as `len(items) - n` gives `len(items)` for n == 0, so the slice is empty.
- **`max(..., 0)` matters too.** For 7 items and `n = 10`, `len(items) - n` is `-3`, which Python reads as "3 from the end", not "before the start". `max` keeps the start at 0, so you get all 7.
- **Both return new lists**, because every slice is a new (shallow) list. The test that appends to the result checks exactly that.

**Alternatives**

- `return items[-n:] if n else []` is also correct for `last`. It's shorter, but the special case is easy to forget, which is the point of the test.
- For real APIs, page by an offset and a limit (`items[offset:offset + limit]`) or by a cursor. The slicing logic is the same.
