```python
def log_line(level, *words, ts=None, **fields):
    parts = [level.upper(), *words]
    if ts is not None:
        parts.insert(0, ts)
    for key in sorted(fields):
        value = str(fields[key])
        if " " in value:
            value = f'"{value}"'
        parts.append(f"{key}={value}")
    return " ".join(parts)
```

**Why it works**

- **The signature is the validation.** `level` is an ordinary parameter, so `log_line()` fails with `TypeError: log_line() missing 1 required positional argument: 'level'` before your body runs. `log_line("info", level="debug")` gives `got multiple values for argument 'level'`. In Go the compiler checks a call against the signature. Python does the same check at call time.
- **`*words` collects the extra positional arguments into a tuple.** Everything after it in the `def` is keyword-only, so `ts` can never be filled positionally: `log_line("info", "boot", "12:00")` puts `"12:00"` into `words`.
- **`**fields` collects the remaining keyword arguments into a dict.** `ts` is a named parameter, so it never appears in `fields`. A `ts=` field is therefore impossible, which is a deliberate trade-off.
- **`sorted(fields)` sorts the keys,** so the output is deterministic whatever order the caller used. Logs that are grep-able and diff-able need that.
- **`ts is not None`** rather than `if ts:`: an empty-string timestamp is odd, but it is still "given". Use truthiness only when every falsy value really means "missing".
- `[level.upper(), *words]` uses `*` to unpack inside a list literal, the same unpacking you used in calls.

**Alternatives**

- `" ".join([...])` with a comprehension for the fields, once you're comfortable with PY.M03 comprehensions.
- In real code, use the standard `logging` module, or a structured-logging library, instead of building lines by hand. This exercise is about signatures, not about logging.
