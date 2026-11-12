```python
async def fetch_quotes(symbols: list[str], get_quote: GetQuote) -> dict[str, float]:
    unique = list(dict.fromkeys(symbols))
    async with asyncio.TaskGroup() as tg:
        tasks = {symbol: tg.create_task(get_quote(symbol)) for symbol in unique}
    return {symbol: task.result() for symbol, task in tasks.items()}
```

**Why it works**

- **`dict.fromkeys(symbols)`** keeps the first occurrence of each symbol in order, so duplicates are fetched once and the order is the input order.
- **`tg.create_task(...)` schedules every lookup before any of them is awaited.** The loop starts them as soon as this coroutine suspends, which happens when the `async with` block ends and the TaskGroup waits for its tasks. All lookups are in flight at once, so the total time is about the slowest lookup, not the sum.
- **The block only exits when every task is done**, so `task.result()` is safe afterwards. The result is built from the `tasks` dict, which is in input order, so completion order doesn't matter.

**Alternative with gather (same behaviour here):**

```python
unique = list(dict.fromkeys(symbols))
prices = await asyncio.gather(*(get_quote(s) for s in unique))
return dict(zip(unique, prices))
```

`gather` returns results in the order of its arguments, so `zip` pairs them correctly. The difference shows up when a lookup fails (L02): the TaskGroup cancels the remaining lookups, while gather lets them keep running.

**Common mistakes:** creating tasks inside the loop but awaiting each one immediately (still sequential), or building the dict in the order tasks complete.
