```python
async def pull_pages(name: str, pages: int, log: list[str]) -> None:
    for i in range(pages):
        log.append(f"{name}{i}")
        await asyncio.sleep(0.01)  # suspends this task; the loop runs others


async def checksum(rows: list[str], log: list[str], every: int = 100) -> int:
    if every < 1:
        raise ValueError("every must be >= 1")
    total = 0
    for n, row in enumerate(rows, start=1):
        total += sum(row.encode())
        if n % every == 0:
            await asyncio.sleep(0)  # let other tasks run
    log.append("checksum done")
    return total
```

**Why it works**

- **`time.sleep` blocks the thread, and the event loop lives on that thread.** While `a` sleeps that way, nothing else runs, so `b` can't start until `a` has finished. `await asyncio.sleep(0.01)` suspends only the current task: the loop runs `b` while `a` waits. That's why `b0` now comes before `a1`.
- **A loop with no `await` is one uninterrupted step for the event loop.** asyncio never preempts a task, unlike Go's scheduler, which (since Go 1.14) can preempt a goroutine anywhere. `asyncio.sleep(0)` is the documented way to say "let others run now" without actually waiting.
- **Yield every `every` rows, not every row.** Each switch costs a trip through the event loop. Yielding every 100 rows keeps the loop responsive and the overhead small.
- **Validate before working.** With `every=0`, `n % every` would raise `ZeroDivisionError` on the first row, which is a confusing error for a caller. Checking up front turns it into a clear `ValueError`.

**Alternatives**

- If the CPU work is big, yielding only spreads it out: the total CPU time still runs on the loop thread. Moving it to a process pool (`loop.run_in_executor` with `ProcessPoolExecutor`) frees the loop completely and can use other cores. L03 covers this.
- `asyncio.to_thread(checksum_sync, rows)` would keep the loop responsive too, but because of the GIL it won't make pure-Python CPU work faster.
