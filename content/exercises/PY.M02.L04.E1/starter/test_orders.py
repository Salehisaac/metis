# Every test builds its own orders, so each one also fails or passes when run alone (pytest -k NAME).
from orders import BLANK_ORDER, add_item, add_note, new_order


def test_new_order_fields():
    assert new_order(7, ["pen"]) == {"status": "new", "items": ["pen"], "notes": [], "id": 7}


def test_default_orders_do_not_share_items():
    first = new_order(1)
    second = new_order(2)
    add_item(first, "pen")
    assert first["items"] == ["pen"]
    assert second["items"] == []


def test_callers_list_is_not_shared():
    initial = ["pen"]
    order = new_order(1, initial)
    add_item(order, "ink")
    assert order["items"] == ["pen", "ink"]
    assert initial == ["pen"]


def test_empty_list_from_caller_is_not_shared():
    initial = []
    order = new_order(1, initial)
    add_item(order, "ink")
    assert initial == []


def test_notes_are_not_shared_between_orders():
    first = new_order(1)
    second = new_order(2)
    add_note(first, "gift wrap")
    assert first["notes"] == ["gift wrap"]
    assert second["notes"] == []


def test_blank_order_never_changes():
    order = new_order(1)
    add_item(order, "pen")
    add_note(order, "fragile")
    assert BLANK_ORDER == {"status": "new", "items": [], "notes": []}
