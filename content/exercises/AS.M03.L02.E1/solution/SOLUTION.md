```python
async def smoke(app, paths, concurrency):
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    unique = list(dict.fromkeys(paths))
    limit = asyncio.Semaphore(concurrency)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        async def status(path: str) -> int:
            async with limit:
                response = await client.get(path)
                return response.status_code

        codes = await asyncio.gather(*(status(p) for p in unique))
    return dict(zip(unique, codes))
```

**Why it works**

- **`httpx.ASGITransport(app=app)`** makes the `AsyncClient` call the app directly, in the same event loop, with no server or socket. `base_url` is required so relative paths like `/ok/1` form a full URL; the host name is arbitrary.
- **`raise_app_exceptions=False`**: by default the transport re-raises an exception from a handler (handy in tests, where you want the traceback). A smoke tester wants the HTTP view instead: the app's error handling turns the `RuntimeError` into a 500 response.
- **One client for all requests**, created with `async with` so it's closed even if something fails. The inner coroutine `status` closes over `client` and `limit`, so it has to be defined inside the `async with` block.
- **Semaphore + gather** come straight from AS.M02: all requests are scheduled at once, the semaphore keeps at most `concurrency` of them inside `client.get`, and gather returns codes in argument order, so `zip` pairs them with the paths.
- **`dict.fromkeys(paths)`** drops duplicates while keeping order.

**Alternatives**

- A `TaskGroup` instead of gather works the same here, because nothing is expected to raise: errors are status codes.
- In real smoke tests against a deployed service, swap the transport for a real base URL (`AsyncClient(base_url="https://staging...")`); the rest of the code stays the same. That's a nice property of testing through httpx.
