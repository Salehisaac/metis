```python
def new_order(order_id: int, items: list[str] | None = None) -> dict:
    order = copy.deepcopy(BLANK_ORDER)
    order["id"] = order_id
    if items is not None:
        order["items"] = list(items)
    return order
```

**Three shared-state bugs, one idea: an order must own every mutable object inside it.**

1. **Mutable default (`items=[]`).** The default list is created once, when `def` runs. Every `new_order(...)` without items stored *that same list* as `order["items"]`, so adding a pen to one order added it to every default order. `items=None` plus a check `is None` gives each call its own list.
2. **Aliasing the caller's list (`order["items"] = items`).** That stores a second label for the caller's list, so `add_item` changed the caller's `initial` list. `list(items)` builds a new list with the same items. (A shallow copy is enough: the items are strings, which are immutable.)
3. **Shallow copy of the template (`BLANK_ORDER.copy()`).** The new dict's `"notes"` slot pointed at the same list as `BLANK_ORDER["notes"]`, so a note on one order appeared on the template and on every later order. `copy.deepcopy(BLANK_ORDER)` copies the inner lists too, which also means `order["items"]` is already a new `[]` when no items are passed.

Notice that `test_new_order_fields` can pass or fail in the starter depending on which tests ran first: the corrupted default and template are module-level state that survives between tests. That order-dependence is itself a symptom of shared mutable state.

**Alternatives**

- `items=()` (an immutable tuple) is also a safe default, since `list(())` gives a new empty list. `None` is the common convention.
- Instead of `deepcopy`, build the dict explicitly: `{"status": "new", "items": [], "notes": [], "id": order_id}`. That's faster and clearer, but you then have to keep it in sync with the template by hand.
- `items or []` would *seem* to work here, but with `order["items"] = items or []` the caller's non-empty list would still be shared. Copy it either way.
