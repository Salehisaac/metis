```python
class PortError(ValueError):
    pass


def parse_port(text: str) -> int:
    try:
        port = int(text)
    except ValueError as err:
        raise PortError(f"invalid port {text!r}") from err
    if not 1 <= port <= 65535:
        raise PortError(f"port {port} out of range 1-65535")
    return port
```

**Go to Python, line by line**

| Go | Python |
|---|---|
| `var ErrPort = errors.New("port")` (sentinel) | `class PortError(ValueError): pass` (a type you catch by class) |
| `n, err := strconv.Atoi(...)` / `if err != nil` | `try: port = int(text)` / `except ValueError as err:` |
| `fmt.Errorf("invalid port %q: %w", s, err)` | `raise PortError(f"invalid port {text!r}") from err` |
| `errors.Is(err, ErrPort)` | `except PortError:`, or `isinstance(e, PortError)` |
| `return n, nil` | `return port` (success needs no error value) |

**Why it works**

- `int()` already ignores surrounding whitespace (`int(" 443\n")` is 443), so the Go `TrimSpace` isn't needed.
- **Only `int()` is inside `try`.** If the range check were inside too, nothing would break today. But each extra line in a `try` is a line whose errors you might catch by accident.
- **`from err`** sets `__cause__`, like `%w`. The traceback then shows the original error with "The above exception was the direct cause of the following exception". Without `from`, Python still records the original as `__context__` ("During handling of the above exception, another exception occurred"), which reads like a second bug. That's why `test_not_a_number_keeps_the_cause` checks `__cause__`.
- **The range error is a new failure, not a translation,** so it has no cause, which is what `test_range_error_has_no_cause` checks.
- **Subclassing `ValueError`** means a caller that writes `except ValueError` (the generic "bad value" family) still works, while a caller that wants only port problems writes `except PortError`. That's the hierarchy doing what `errors.Is` does with wrapping.

**Alternative:** check `text.strip().isdigit()` first (LBYL) instead of catching. That rejects `+80` and `-1` as "invalid" rather than "out of range", so it changes the contract. And `int()` already does that parsing, so asking forgiveness is simpler here.
