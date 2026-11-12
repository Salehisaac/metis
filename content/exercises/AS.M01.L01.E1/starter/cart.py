"""Shopping-cart totals backed by a (fake) async inventory service.

The service functions are correct. cart_total and checkout_message have bugs: fix them.
"""
import asyncio

STOCK = {"tea": 3, "mug": 0, "pot": 1}
PRICES = {"tea": 4, "mug": 9, "pot": 25}


async def in_stock(sku: str) -> bool:
    """Ask the inventory service whether sku can be shipped. Correct, don't change."""
    await asyncio.sleep(0)  # stands in for a network round trip
    return STOCK.get(sku, 0) > 0


async def price_of(sku: str) -> int:
    """Ask the pricing service for sku's price. Correct, don't change."""
    await asyncio.sleep(0)
    return PRICES[sku]


async def cart_total(skus: list[str]) -> int:
    """Sum the prices of the skus that are in stock; skip the others."""
    total = 0
    for sku in skus:
        if in_stock(sku):
            total += price_of(sku)
    return total


async def checkout_message(skus: list[str]) -> str:
    """'Total: N' for the cart, or 'Nothing to ship' when the total is 0."""
    total = cart_total(skus)
    if total == 0:
        return "Nothing to ship"
    return f"Total: {total}"
