```python
async def locate_all(cities: list[str], geocode: Callable[[str], Coords]) -> dict[str, Coords]:
    result: dict[str, Coords] = {}
    for city in cities:
        if city not in result:
            result[city] = await asyncio.to_thread(geocode, city)
    return result
```

**Why it works**

- **`asyncio.to_thread(geocode, city)` runs `geocode(city)` in a worker thread** and returns an awaitable. Awaiting it suspends *this* coroutine, and the event loop is free to run the heartbeat (or, in a server, other requests) while the worker thread blocks on the network.
- **Errors come back through the `await`.** If `geocode` raises `LookupError` in the worker thread, `await asyncio.to_thread(...)` raises the same exception in the coroutine. That's why no `try/except` is needed for the test that checks propagation.
- **`if city not in result`** skips duplicates, and a dict keeps insertion order, so the keys come out in first-seen order.
- **This is the one place in AS.M01 where a thread *is* involved, and you asked for it explicitly.** `await` alone never creates a thread; `to_thread` does.

**Alternatives and limits**

- **Concurrent lookups:** the cities are looked up one at a time (each in a thread, but sequentially). With `asyncio.gather` or a `TaskGroup` (AS.M02) you could run several `to_thread` calls at once. The default thread pool is limited, so you'd also bound how many run at a time (AS.M02.L04).
- **A native async client** (for HTTP, `httpx.AsyncClient`) avoids threads entirely and scales better than one thread per waiting call. Use `to_thread` when the only library you have is sync.
- **CPU-bound work:** `to_thread` keeps the loop responsive, but because of the GIL pure-Python CPU work won't get faster. Use a `ProcessPoolExecutor` for that.
