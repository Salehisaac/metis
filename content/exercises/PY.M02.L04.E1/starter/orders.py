"""Order factory for a small shop."""

import copy  # noqa: F401  (you may need it)

BLANK_ORDER = {"status": "new", "items": [], "notes": []}


def new_order(order_id: int, items: list[str] = []) -> dict:
    """Return a fresh order: BLANK_ORDER's fields plus "id".

    `items` are the initial items. The order gets its own list: it is never shared with
    the caller, with BLANK_ORDER, or with any other order. Nothing in an order is
    shared with anything else.
    """
    order = BLANK_ORDER.copy()
    order["id"] = order_id
    order["items"] = items
    return order


# These two are correct. Don't change them.
def add_item(order: dict, item: str) -> None:
    order["items"].append(item)


def add_note(order: dict, note: str) -> None:
    order["notes"].append(note)
