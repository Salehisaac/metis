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
