```python
VALID = [
    ("90s", 90),
    ("2m", 120),
    ("1h", 3600),             # hours: catches a wrong multiplier
    ("1h30m", 5400),          # two units together
    ("1h2m3s", 3723),         # all three units
    ("0s", 0),                # zero is valid: catches a truthiness check
    ("  5m ", 300),           # surrounding whitespace is ignored
]

INVALID = [
    "abc",
    "",                       # empty
    "   ",                    # blank: only whitespace
    "30m1h",                  # wrong order
    "1m1m",                   # unit repeated
    "10",                     # number without a unit
    "h",                      # unit without a number
    "1.5h",                   # decimal
    "-5s",                    # sign
    "1H",                     # uppercase unit
    "1h 30m",                 # inner space
]


@pytest.mark.parametrize("text", INVALID)
def test_invalid(text):
    with pytest.raises(ValueError, match="invalid duration"):
        parse_duration(text)
```

**Which row kills which bug**

| Bug | Spec rule it breaks | Row that exposes it |
|---|---|---|
| `bug_no_strip` | surrounding whitespace is ignored | `("  5m ", 300)` raises instead |
| `bug_empty_accepted` | `''` is invalid | `""` returns 0 instead of raising |
| `bug_blank_accepted` | `'   '` is invalid | `"   "` returns 0 instead of raising |
| `bug_zero_rejected` | `'0s'` is 0 | `("0s", 0)` raises instead |
| `bug_hours_as_minutes` | an hour is 3600 s | `("1h", 3600)` gives 60 |
| `bug_any_order` | h, m, s in order, each at most once | `"30m1h"` and `"1m1m"` are accepted |

The two starter rows (`90s`, `2m`) and `"abc"` kill none of them. Tests built only from the "nice" example pass on every buggy version. That's the I1 lesson again: the bug hides in the inputs you didn't try.

**Why the rows look like this**

- **One row per spec bullet, plus its opposite.** "Surrounding whitespace is fine" produces `'  5m '` (valid) and `'1h 30m'` (invalid). "In order h, m, s" produces `'1h30m'` and `'30m1h'`.
- **"Nothing" inputs:** `''`, `'   '` and zero. `''` and `'   '` are two separate rows because they can fail separately (`bug_blank_accepted` handles `''` correctly).
- **Rows that kill no bug still earn their place** (`'1.5h'`, `'-5s'`, `'1H'`): they pin the spec, so a future refactor (say, replacing the regex) can't quietly start accepting them.
- **`match="invalid duration"`** makes sure the `ValueError` is *this function's* error, not some unrelated `ValueError` from inside it (an `int()` call on the wrong group, say).

**Alternative:** `pytest.param("", id="empty")` gives readable test ids for awkward values; the default id for `""` is `test_invalid[]`.
