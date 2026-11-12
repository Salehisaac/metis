class Inventory:
    """Stock counts per SKU (product code) for one warehouse."""

    def __init__(self) -> None:
        raise NotImplementedError

    @classmethod
    def from_counts(cls, counts: dict[str, int]) -> "Inventory":
        """Build an inventory from {sku: qty}. Every qty must be positive."""
        raise NotImplementedError

    def add(self, sku: str, qty: int) -> None:
        raise NotImplementedError

    def remove(self, sku: str, qty: int) -> None:
        raise NotImplementedError

    def count(self, sku: str) -> int:
        raise NotImplementedError

    @property
    def total(self) -> int:
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError
