import asyncio
import inspect


def run(coro):
    return asyncio.run(coro)


def test_total_of_items_in_stock():
    import cart
    assert run(cart.cart_total(["tea", "pot"])) == 29


def test_out_of_stock_items_are_skipped():
    import cart
    assert run(cart.cart_total(["tea", "mug", "tea"])) == 8


def test_empty_cart_totals_zero():
    import cart
    assert run(cart.cart_total([])) == 0


def test_unknown_sku_is_skipped():
    import cart
    assert run(cart.cart_total(["ghost", "tea"])) == 4


def test_message_with_total():
    import cart
    assert run(cart.checkout_message(["pot"])) == "Total: 25"


def test_message_when_nothing_ships():
    import cart
    assert run(cart.checkout_message(["mug"])) == "Nothing to ship"


def test_functions_stay_async():
    import cart
    assert inspect.iscoroutinefunction(cart.cart_total)
    assert inspect.iscoroutinefunction(cart.checkout_message)
