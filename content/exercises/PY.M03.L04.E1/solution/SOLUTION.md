```python
def parse_settings(text: str) -> dict[str, str]:
    settings = {}
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"line {number}: expected 'key = value', got {stripped!r}")
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"line {number}: empty key")
        settings[key] = value.strip()
    return settings


def parse_list(value: str) -> list[str]:
    items = []
    for part in value.split(","):
        part = part.strip()
        if part:
            items.append(part)
    return items
```

**Why it works**

- **Strip first, then decide.** `line.strip()` turns a whitespace-only line into `""`, which is falsy, so one `if not stripped` skips every kind of blank line. Checking `startswith("#")` on the *stripped* line also catches indented comments.
- **Check before unpacking.** Without the `"=" in stripped` check, `key, value = "just some words".split("=", 1)` would raise `ValueError: not enough values to unpack`. That's the right type, but the message doesn't tell the user which line is wrong.
- **`split("=", 1)`** cuts at the first `=` only, so `dsn = user=app password=s3cret` keeps the whole connection string as the value. Both halves still carry the spaces next to the `=`, so both are stripped.
- **Empty value vs empty key:** `"debug ="` gives `value == ""`, which is allowed. `" = value"` gives `key == ""`, which is not.
- **Line numbers** come from `enumerate(..., start=1)`, and blank lines are counted too, so the number matches what an editor shows.
- **`parse_list`** relies on `split(",")` keeping empty fields: `" a, b,,c ,"` gives `[' a', ' b', '', 'c ', '']`. Stripping and dropping the empty ones gives `['a', 'b', 'c']`. For `""`, `split(",")` returns `['']`, which is also dropped, so the result is `[]`. `split()` with no argument would be wrong here: it would break `"New York"` into two items.

**Alternatives**

- `text.splitlines()` vs `text.split("\n")`: both pass the tests. `splitlines()` also handles Windows `\r\n` line endings and doesn't produce a final empty line for a trailing newline (`"a\r\nb\n".splitlines()` is `['a', 'b']`).
- After L05: `[p.strip() for p in value.split(",") if p.strip()]` is the one-line `parse_list`.
- Real projects: `configparser` for INI files, or environment variables read by a settings library. Hand-rolled parsing is for learning and for tiny formats.
