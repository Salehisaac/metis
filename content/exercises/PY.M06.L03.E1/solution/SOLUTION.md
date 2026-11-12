```python
"""Invoice helpers. Behaviour is documented in each docstring; keep it."""


def add_line(item: str, price: float, lines: list[tuple] | None = None) -> list[tuple]:
    """Append (item, price) to lines and return it. Without lines, start a new list."""
    if lines is None:
        lines = []
    lines.append((item, price))
    return lines


def parse_price(text: str) -> float | None:
    """'12.50' -> 12.5; text that isn't a number -> None."""
    try:
        return float(text)
    except ValueError:
        return None


def total(lines: list[tuple]) -> float:
    """Sum of the prices, rounded to 2 decimals. Empty -> 0.0."""
    result = 0.0
    for _item, price in lines:
        result += price
    return round(result, 2)


def is_free(price: float) -> bool:
    """True when the price is exactly 0."""
    return price == 0


def describe(item: str, price: float | None) -> str:
    """'tea', 3.5 -> 'tea: 3.50'; a missing price -> 'tea: ?'."""
    if price is None:
        return f"{item}: ?"
    return f"{item}: {price:.2f}"
```

**What each rule was telling you** (ruff 0.17.3)

| Rule | Fix | Why it matters |
|---|---|---|
| F401 `os` imported but unused | removed by `--fix` | dead imports slow startup and hide real dependencies |
| UP035 / UP006 / UP045 | `--fix` turned `List[...]` into `list[...]` and `Optional[X]` into `X \| None` | the modern spelling since Python 3.9 / 3.10; `--target-version py312` allows it |
| B006 mutable default | `None` default plus a new list inside | the starter shared **one** list between calls, so the second `add_line("cake", 4.0)` returned both lines. This was the failing test |
| E722 bare `except` | `except ValueError` | a bare except also swallows `KeyboardInterrupt`, `TypeError` from a wrong call, and so on. `float()` signals bad text with ValueError |
| F841 unused `label` | delete the line, then rename the loop variable to `_item` | the computation did nothing. A leading underscore says "unused on purpose" |
| SIM103 needless bool | `return price == 0` | the comparison already is the bool |
| E711 `== None` | `is None` | `None` is a singleton, and `==` can be overridden by a class |

**Why not just `--unsafe-fixes`?** Try it with `--diff`. For B006 it writes `lines: list[tuple] = None`, which fixes the bug but leaves a type hint that is now wrong. For F841 it keeps `item.upper()` as a bare expression to preserve a possible side effect, so the useless call stays. "Unsafe" means *may change meaning, so read before you accept*.

Finally `ruff format` joined the `def add_line(...)` line to fit the 88-character limit, switched to double quotes, and added a blank line after the module docstring.
