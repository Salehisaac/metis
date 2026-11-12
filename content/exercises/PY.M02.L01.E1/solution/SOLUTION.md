```python
def changed_fields(old: dict, new: dict) -> list[str]:
    changed = []
    for key in old:
        if old[key] != new[key]:
            changed.append(key)
    return changed


def save_version(history: list, record: dict) -> None:
    history.append(dict(record))
```

**Bug 1: `is not` compares objects, not values.** `["go", "py"]` in `old` and `["go", "py"]` in `new` are two separate list objects (two literals always create two lists), so `is not` says "changed" although the values are equal. `!=` compares values. `None` worked by luck of the rule: `None` is a singleton, so `is` and `==` agree on it. `"ali" is "ali"` also happened to pass here, because CPython reuses the object for two equal string literals in one file. That's an implementation detail, which is exactly why `is` is the wrong tool for values.

**Bug 2: `append(record)` stores an alias.** The history then holds a second label for the caller's dict, so `record["role"] = "lead"` rewrites the "old" snapshot too: both entries end up showing `lead`. `dict(record)` (or `record.copy()`) creates a new dict, so the snapshot is its own object. Mutating `history` itself is fine: the docstring says "in place".

**Limit:** `dict(record)` is a *shallow* copy. If the caller later did `record["langs"].append("sql")`, the snapshot's `langs` list would change too, because both dicts point at the same inner list. For nested data use `copy.deepcopy(record)` (lesson L04).

**Alternatives:** `[key for key in old if old[key] != new[key]]` is the same logic as one expression (list comprehensions come in PY.M03).
