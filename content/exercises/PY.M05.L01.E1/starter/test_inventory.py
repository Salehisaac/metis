import pytest


def test_add_and_count():
    from inventory import Inventory
    inv = Inventory()
    inv.add("apple", 3)
    inv.add("apple", 2)
    inv.add("pear", 1)
    assert inv.count("apple") == 5
    assert inv.count("pear") == 1


def test_count_unknown_sku_is_zero():
    from inventory import Inventory
    assert Inventory().count("kiwi") == 0


def test_inventories_do_not_share_stock():
    from inventory import Inventory
    north, south = Inventory(), Inventory()
    north.add("apple", 3)
    assert south.count("apple") == 0


def test_add_rejects_non_positive_qty():
    from inventory import Inventory
    inv = Inventory()
    for bad in (0, -1):
        with pytest.raises(ValueError):
            inv.add("apple", bad)
    assert inv.count("apple") == 0


def test_remove_too_many_raises_and_keeps_stock():
    from inventory import Inventory
    inv = Inventory()
    inv.add("apple", 2)
    with pytest.raises(ValueError):
        inv.remove("apple", 3)
    with pytest.raises(ValueError):
        inv.remove("kiwi", 1)
    with pytest.raises(ValueError):
        inv.remove("apple", 0)
    assert inv.count("apple") == 2


def test_remove_to_zero_drops_sku():
    from inventory import Inventory
    inv = Inventory()
    inv.add("apple", 2)
    inv.add("pear", 1)
    inv.remove("apple", 2)
    assert inv.count("apple") == 0
    assert repr(inv) == "Inventory({'pear': 1})"


def test_from_counts_copies_and_validates():
    from inventory import Inventory
    counts = {"apple": 3}
    inv = Inventory.from_counts(counts)
    assert isinstance(inv, Inventory)
    counts["apple"] = 100
    inv.add("pear", 1)
    assert inv.count("apple") == 3
    assert counts == {"apple": 100}
    with pytest.raises(ValueError):
        Inventory.from_counts({"apple": 1, "pear": 0})


def test_total_is_a_property():
    from inventory import Inventory
    inv = Inventory()
    assert inv.total == 0
    inv.add("apple", 3)
    inv.add("pear", 2)
    assert inv.total == 5
