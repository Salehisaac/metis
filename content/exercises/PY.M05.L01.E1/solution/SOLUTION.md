```python
class Inventory:
    """Stock counts per SKU (product code) for one warehouse."""

    def __init__(self) -> None:
        self._stock: dict[str, int] = {}

    @classmethod
    def from_counts(cls, counts: dict[str, int]) -> "Inventory":
        """Build an inventory from {sku: qty}. Every qty must be positive."""
        inv = cls()
        for sku, qty in counts.items():
            inv.add(sku, qty)
        return inv

    def add(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError(f"qty must be positive, got {qty}")
        self._stock[sku] = self._stock.get(sku, 0) + qty

    def remove(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError(f"qty must be positive, got {qty}")
        have = self.count(sku)
        if qty > have:
            raise ValueError(f"cannot remove {qty} {sku}: only {have} in stock")
        if qty == have:
            del self._stock[sku]
        else:
            self._stock[sku] = have - qty

    def count(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    @property
    def total(self) -> int:
        return sum(self._stock.values())

    def __repr__(self) -> str:
        return f"Inventory({self._stock!r})"
```

**Why it works**

- **State lives on the instance.** `self._stock = {}` runs in `__init__`, so every `Inventory()` gets its own dict. A dict written at class level (`_stock = {}` under `class Inventory:`) would be one dict shared by all warehouses, and `test_inventories_do_not_share_stock` catches that.
- **`from_counts` is the Python version of a Go `NewInventoryFromCounts`.** It's a `@classmethod`, so it receives the class as `cls` and builds the object with `cls()`. Going through `add` gives two things for free: every quantity is validated, and the input dict is *copied* entry by entry. `self._stock = counts` would alias the caller's dict (PY.M02), so their later changes would leak into your inventory, and your changes into theirs.
- **Validate before you mutate.** `remove` checks everything first and only then changes `_stock`, so a rejected call leaves the stock exactly as it was. That's the "error leaves state unchanged" rule.
- **`total` is a `@property`.** Callers write `inv.total`, like a field, but it's computed from `_stock` each time, so it can never go stale.
- The leading underscore in `_stock` says "internal, don't touch". Python doesn't enforce it; it's the convention that replaces Go's lowercase (unexported) names.

**Alternatives**

- `collections.Counter` (PY.M03) could hold the stock, but you'd still need the validation, and `Counter` keeps zero or negative counts unless you remove them yourself.
- `from_counts` could check every quantity first and then do `inv._stock = dict(counts)`. That's fine too, as long as it's a copy.
