```python
def parse_lines(lines):
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        message = parts[1] if len(parts) == 2 else ""
        yield parts[0].upper(), message


def only_level(records, level):
    wanted = level.upper()
    for record in records:
        if record[0] == wanted:
            yield record


def first_n(items, n):
    if n <= 0:
        return
    count = 0
    for item in items:
        yield item
        count += 1
        if count == n:
            return
```

**Why it works**

- Each function contains `yield`, so calling it only creates a generator. No line is read until someone calls `next()` on the last stage, and then each stage pulls exactly one item from the stage before it. That's why the pipeline works on the tests' endless log source.
- `raw.strip()` removes the `"\n"` that file lines keep, plus surrounding spaces. Stripping *before* the blank check means `"   "` counts as blank.
- `split(maxsplit=1)` splits on the first run of whitespace only, so `"WARN  disk 91%"` gives `["WARN", "disk 91%"]` and the message keeps its inner spaces. `"DEBUG"` gives one part, so the message is `""`.
- `level.upper()` is computed once, outside the loop.

**The first_n trap.** This version is wrong:

```python
count = 0
for item in items:
    if count == n:
        return          # too late: the for loop already pulled item n+1
    yield item
    count += 1
```

The `for` statement calls `next()` *before* the body runs, so by the time you check, item n+1 has been taken from the source and is lost. On a shared iterator (a file, a socket, a Kafka consumer) that item is gone for the next reader. Yield first, then check. And `n <= 0` must return before the loop, or the loop pulls one item.

**Alternatives**

- `itertools.islice(items, n)` does exactly what first_n does (for n >= 0) and is what you'd use in real code. You wrote it by hand to see why the order matters.
- `only_level` as a generator expression: `return (r for r in records if r[0] == level.upper())`. Same laziness, but the function is then a normal function returning a generator.
- A `return` inside a generator just ends the iteration (the caller sees `StopIteration`); a value after `return` would not be yielded.
