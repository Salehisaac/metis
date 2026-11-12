```python
class BadRecord(ValueError):
    """A line that isn't a valid 'name,score' record."""


def parse_record(line: str, lineno: int) -> tuple[str, int]:
    parts = line.split(",")
    if len(parts) != 2 or not parts[0].strip():
        raise BadRecord(f"line {lineno}: expected 'name,score', got {line!r}")
    name, score = parts
    try:
        value = int(score)
    except ValueError as err:
        raise BadRecord(f"line {lineno}: bad score {score.strip()!r}") from err
    return name.strip(), value


def load_scores(lines: list[str]) -> tuple[dict[str, int], int]:
    scores = {}
    skipped = 0
    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            name, score = parse_record(line, lineno)
        except BadRecord:
            skipped += 1
        else:
            scores[name] = score
    return scores, skipped
```

**What was wrong, and why each fix matters**

1. **The bare `except:` caught everything,** including the `AttributeError` from `None.split`, which is a bug in the caller. A real program would have silently produced a smaller result. `except ValueError` around `int()` only handles "this text isn't a number". `None` now fails loudly where it entered, like a Go `err` you didn't discard.
2. **Returning `None` instead of raising** threw away *why* the line was bad. Every caller then has to remember `if record:`, exactly like checking a Go error, but without the compiler forcing it. Now the reason travels with the exception: line number, text, and the original `int()` error as `__cause__`.
3. **`skipped` was always 0.** Counting is a policy decision, and it belongs to `load_scores`, which knows it is processing many lines. `parse_record` only knows one line, so it raises and lets the caller decide.
4. **`try/except/else`:** only the call that can raise `BadRecord` is inside `try`. Storing the result is in `else`, so a bug in that line (a typo, say) couldn't be mistaken for a bad record.
5. **The shape check is LBYL on purpose.** `name, score = line.split(",")` would also raise `ValueError` for the wrong count, but then you would need a second `except` to produce a different message, and an empty name isn't an exception at all. Checking `len(parts)` first is clearer here.

**Alternatives:** collect the error messages (`errors.append(str(e))`) instead of only counting them, so a CLI can print a warning such as "skipped 2 lines: line 2: ...". PRJ-01 asks for something like this. The `csv` module handles quoting when names can contain commas.
