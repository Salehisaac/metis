```python
async def cart_total(skus: list[str]) -> int:
    """Sum the prices of the skus that are in stock; skip the others."""
    total = 0
    for sku in skus:
        if await in_stock(sku):
            total += await price_of(sku)
    return total


async def checkout_message(skus: list[str]) -> str:
    """'Total: N' for the cart, or 'Nothing to ship' when the total is 0."""
    total = await cart_total(skus)
    if total == 0:
        return "Nothing to ship"
    return f"Total: {total}"
```

**Why it works**

- **Three missing `await`s.** `in_stock(sku)`, `price_of(sku)` and `cart_total(skus)` each return a *coroutine object*, not a value. `await` runs the coroutine to completion (suspending this one whenever it waits) and gives you its return value.
- **The sneaky one is `if in_stock(sku):`.** A coroutine object is an ordinary object, so it is always truthy. Before the fix, `mug` (out of stock) would have been charged. Missing awaits rarely crash at the spot of the bug: they give you a wrong value that crashes later, or never.
- **`total == 0` without the await** compares a coroutine object with 0. That's `False`, so the starter returned `"Total: <coroutine object ...>"` instead of `"Nothing to ship"`.
- **No threads appear anywhere.** All of this runs on the one thread that `asyncio.run` uses.

**How to spot it next time:** pytest prints `RuntimeWarning: coroutine 'in_stock' was never awaited`. Treat that warning as a bug report. Type checkers (mypy, pyright) flag it as well, because they know `in_stock` returns `Coroutine[..., bool]`, not `bool`.

**Alternative:** the stock check and the price lookup for different skus are independent, so they could run concurrently with `asyncio.gather` or a `TaskGroup` (AS.M02). Sequential awaits are correct here, just not as fast as they could be.
