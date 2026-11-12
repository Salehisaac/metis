# Each order is a dict like {"id": 7, "customer": "mina", "cents": 1250, "status": "paid"}.
# status is one of "paid", "pending", "refunded". Money is in integer cents.


def paid_ids(orders: list[dict]) -> list[int]:
    """Ids of the paid orders, in input order."""
    raise NotImplementedError


def cents_by_id(orders: list[dict]) -> dict[int, int]:
    """Map every order id to its cents."""
    raise NotImplementedError


def customers_with(orders: list[dict], status: str) -> list[str]:
    """Distinct customers having at least one order with this status, sorted alphabetically."""
    raise NotImplementedError


def revenue(orders: list[dict]) -> int:
    """Total cents of the paid orders (0 if there are none)."""
    raise NotImplementedError


def has_order_over(orders: list[dict], limit: int) -> bool:
    """True if any order's cents is strictly greater than limit."""
    raise NotImplementedError
