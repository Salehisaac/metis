```python
async def run_query(pool: Pool, query: str, run: Runner) -> Any:
    conn = pool.acquire()
    try:
        return await run(conn, query)
    finally:
        pool.release(conn)


async def query_or_default(pool, query, run, seconds, default=None):
    try:
        async with asyncio.timeout(seconds):
            return await run_query(pool, query, run)
    except TimeoutError:
        return default
```

**Why it works**

- **`finally` runs on every exit path**: a normal return, an exception from the query, and a `CancelledError` thrown in at the `await`. In the starter, an error or a cancellation at `await run(...)` skipped `pool.release(conn)` and leaked the connection. It's the Go `defer pool.Release(conn)` habit, written as try/finally.
- **`asyncio.timeout(seconds)`** cancels the task when the deadline passes. The cancellation arrives inside `run_query` as a `CancelledError` (so its `finally` releases the connection), and when it reaches the `async with`, the context manager turns it into a `TimeoutError`. That `TimeoutError` can only be caught *outside* the `async with`, which is why the `try` wraps the whole block.
- **No `except CancelledError` at all.** A real cancellation from outside (the test's `task.cancel()`, a client disconnecting, a TaskGroup cancelling siblings) now propagates, so the task ends up `cancelled()`. The starter swallowed it and returned the default, which makes the caller believe the work finished and breaks timeouts and TaskGroups built on top of it.
- **`ValueError` passes through** because only `TimeoutError` is caught.

**Alternative:** `return await asyncio.wait_for(run_query(pool, query, run), seconds)` inside `try/except TimeoutError` behaves the same here. `asyncio.timeout` is the 3.11+ style and can cover several awaits in one block.

**If you must catch `CancelledError`** (for logging, say), re-raise it at the end of the handler: `except asyncio.CancelledError: log(...); raise`.
