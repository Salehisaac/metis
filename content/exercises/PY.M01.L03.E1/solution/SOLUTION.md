```python
def initials(full_name: str) -> str:
    """'ada lovelace' -> 'AL'. Extra spaces are ignored; '' -> ''."""
    result = ""
    for part in full_name.split():
        result += part[0].upper()
    return result
```

**The two bugs, as the failures showed them**

1. **Case:** `assert 'al' == 'AL'` means the right letters but not uppercased. The fix is `part[0].upper()`.
2. **Splitting:** `IndexError: string index out of range` on `part[0]`. `split(" ")` creates empty strings for extra spaces (`"  grace".split(" ")` gives `['', '', 'grace']`), and also for an empty name (`"".split(" ")` gives `['']`). `split()` with no argument splits on runs of whitespace and returns `[]` for an empty name, so the loop doesn't run and the result is `""`.

Notice that `test_single_name` and `test_already_uppercase` passed from the start. Tests that only cover the "nice" inputs would have hidden both bugs.

**Later (PY.M03):** the same thing as one expression, `"".join(p[0].upper() for p in full_name.split())`.
