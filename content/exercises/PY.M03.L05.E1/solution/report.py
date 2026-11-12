# Each order is a dict like {"id": 7, "customer": "mina", "cents": 1250, "status": "paid"}.
# status is one of "paid", "pending", "refunded". Money is in integer cents.


def paid_ids(orders: list[dict]) -> list[int]:
    """Ids of the paid orders, in input order."""
    return [o["id"] for o in orders if o["status"] == "paid"]


def cents_by_id(orders: list[dict]) -> dict[int, int]:
    """Map every order id to its cents."""
    return {o["id"]: o["cents"] for o in orders}


def customers_with(orders: list[dict], status: str) -> list[str]:
    """Distinct customers having at least one order with this status, sorted alphabetically."""
    return sorted({o["customer"] for o in orders if o["status"] == status})


def revenue(orders: list[dict]) -> int:
    """Total cents of the paid orders (0 if there are none)."""
    return sum(o["cents"] for o in orders if o["status"] == "paid")


def has_order_over(orders: list[dict], limit: int) -> bool:
    """True if any order's cents is strictly greater than limit."""
    return any(o["cents"] > limit for o in orders)
