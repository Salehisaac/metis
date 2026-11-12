```python
async def fetch_many(urls, fetch, limit):
    if limit < 1:
        raise ValueError("limit must be >= 1")
    sem = asyncio.Semaphore(limit)

    async def one(url: str) -> str:
        async with sem:
            return await fetch(url)

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(one(url)) for url in urls]
    return [t.result() for t in tasks]
```

**Why it works**

- **The semaphore holds `limit` permits.** Each `one(url)` takes a permit on entering `async with sem` and returns it on leaving, also when `fetch` raises or the task is cancelled. When all permits are taken, the next task waits at `async with sem` until one is released. So at most `limit` fetches are ever in flight, and when there's enough work, exactly `limit` are.
- **All tasks are created up front, in URL order**, and results are read from `tasks` in that order, so completion order doesn't matter.
- **The TaskGroup** propagates a failing fetch (inside an `ExceptionGroup`) and cancels the rest; a cancelled task waiting at the semaphore never acquires a permit, and a running one gives its permit back through `async with`.
- **A new semaphore per call** means two concurrent `fetch_many` calls each get their own limit. A module-level semaphore would also work, but it would be shared by every caller.

**Go comparison:** this is the `sem := make(chan struct{}, limit)` pattern from Effective Go: `sem <- struct{}{}` before the work, `<-sem` after. `errgroup` with `SetLimit(n)` combines both ideas in one type.

**Alternative: a worker pool.** Put the URLs on an `asyncio.Queue` and start `limit` worker tasks that each loop `get()` → fetch → store result by index → `task_done()`. It's more code; it's worth it when the work arrives as a stream rather than as a known list, or when each worker holds an expensive resource (a connection) for its lifetime.
