```python
@app.get("/quote/{country}")
def quote(country: str):  # plain def: FastAPI runs it in its threadpool
    price = carrier_quote(country)
    if price is None:
        raise HTTPException(status_code=404, detail="no service")
    return {"country": country, "eur": price}


@app.get("/quote/{country}/{currency}")
async def quote_in(country: str, currency: str):
    price = await asyncio.to_thread(carrier_quote, country)  # blocking SDK off the loop
    if price is None:
        raise HTTPException(status_code=404, detail="no service")
    rate = await exchange_rate(currency)  # still awaited on the loop
    return {"country": country, currency.lower(): round(price * rate, 2)}
```

**Why it works**

- **`/quote/{country}` only does blocking work**, so the simplest fix is to declare it with plain `def`. FastAPI's docs: a `def` path operation is run in an external threadpool that is then awaited, instead of being called directly (which would block the server). Two requests now block two worker threads, and the event loop stays free, so the barrier sees both calls at once.
- **`/quote/{country}/{currency}` needs both**: a blocking SDK call *and* an `await` (`exchange_rate` is async, and you can only `await` inside `async def`). So it stays `async def`, and the blocking call goes through `asyncio.to_thread`, as in AS.M01.L03.
- **404 still works** in both, because `HTTPException` is raised in the endpoint as before. In the `def` version it's raised in a worker thread, and FastAPI handles it the same way.

**Why the starter failed the concurrency tests:** `async def quote` called `carrier_quote` directly on the event loop's thread. The first request's fake waited at the barrier *holding the loop*, so the second request could never start, and the barrier broke after 1 s (HTTP 500).

**Alternatives**

- Making `quote_in` a `def` and calling `asyncio.run(exchange_rate(...))` inside it would "work", but it starts a new event loop per request inside a worker thread. Don't.
- If the carrier had an async SDK, both endpoints should be `async def` and `await` it, with no threads at all.
- The threadpool is limited (AnyIO's default limiter: 40 threads). Under heavy load, `def` endpoints and `to_thread` calls queue up for threads; a native async client avoids that ceiling.
