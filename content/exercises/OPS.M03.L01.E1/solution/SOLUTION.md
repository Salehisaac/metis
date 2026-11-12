```python
DISCOUNTS = {"WELCOME": 10, "VIP": 25}


def discount_for(code: str | None) -> int:
    """Percent discount for a code; unknown codes give 0. A non-string code is a caller bug."""
    try:
        return DISCOUNTS[code.upper()]
    except KeyError:
        return 0


def basket_total(prices: list[int], codes: list[str] | None = None) -> int:
    """Total in cents after the best discount among codes (the codes list is not modified)."""
    all_codes = [*(codes or []), "NONE"]
    best = max(discount_for(c) for c in all_codes)
    subtotal = sum(prices)
    return subtotal - subtotal * best // 100
```

**How to get there**

1. `../../.venv/bin/ruff check --fix pricing.py` applies the safe fixes: it removes the unused imports (F401), splits and sorts imports (E401, I001) and modernises the annotations (UP006/UP045: `list[int]`, `str | None`).
2. What remains needs a human:
   - **B006, mutable default.** `codes=[]` is created once, when `def` runs, and shared by every call (aliasing, PY.M02). `codes.append("NONE")` also modified the caller's own list. Fix: default `None`, and build a new list.
   - **E722, bare `except`.** It catches everything, including the `AttributeError` from `None.upper()`, so a caller bug looked like "no discount". Catch only `KeyError`, the case you mean (PY.M04).
   - **F841** `unused = ...` and **E711** `prices == None`: delete both; the None check was dead code after `sum(prices)` anyway.
3. `../../.venv/bin/ruff format pricing.py` fixes spacing and blank lines. Then `ruff format --check` exits 0.

**Why the config is fixed**

`select` lists the rule families on purpose: Ruff's built-in default set depends on the Ruff version, and the team wants CI to fail on the same rules on every machine. Turning a rule off to make CI green hides exactly the two bugs above.
