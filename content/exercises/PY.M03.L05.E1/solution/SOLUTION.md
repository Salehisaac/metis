```python
def paid_ids(orders):
    return [o["id"] for o in orders if o["status"] == "paid"]


def cents_by_id(orders):
    return {o["id"]: o["cents"] for o in orders}


def customers_with(orders, status):
    return sorted({o["customer"] for o in orders if o["status"] == status})


def revenue(orders):
    return sum(o["cents"] for o in orders if o["status"] == "paid")


def has_order_over(orders, limit):
    return any(o["cents"] > limit for o in orders)
```

**Why it works**

- **`paid_ids`**: a list comprehension with a filter at the end. It keeps input order because it walks `orders` in order.
- **`cents_by_id`**: a dict comprehension. Order ids are unique, so no key is overwritten. If they weren't unique, the last order would silently win (section 3).
- **`customers_with`**: the set comprehension removes duplicates (mina has two paid orders), and `sorted` turns the unordered set into the alphabetical list the spec asks for. `sorted` always returns a list, so for an unknown status you get `[]`, not `set()`.
- **`revenue`**: a generator expression inside `sum`, so no temporary list is built. `sum` of nothing is 0, so the empty case needs no `if`.
- **`has_order_over`**: `any` with `>` (strict). `any` of nothing is `False`, and it stops at the first match.
- **Integer cents:** money as `int` avoids float rounding (`0.1 + 0.2 != 0.3`). Real systems do the same, or use `Decimal`.

**Alternatives**

- `revenue` as `sum([...])` works but builds a list first; with very many orders the generator expression is lighter.
- `customers_with` as `sorted(set(o["customer"] for o in ...))` is equivalent, just longer.
- Later (PY.M05) the dicts become dataclasses, and `o["status"]` becomes `o.status`. The comprehensions stay the same.
