"""Two async jobs that cooperate with the event loop (reference solution)."""
import asyncio


async def pull_pages(name: str, pages: int, log: list[str]) -> None:
    """Download `pages` pages, appending f"{name}{i}" to log before each one."""
    for i in range(pages):
        log.append(f"{name}{i}")
        await asyncio.sleep(0.01)  # suspends this task; the loop runs others


async def checksum(rows: list[str], log: list[str], every: int = 100) -> int:
    """Sum of the UTF-8 bytes of all rows, yielding to the loop every `every` rows."""
    if every < 1:
        raise ValueError("every must be >= 1")
    total = 0
    for n, row in enumerate(rows, start=1):
        total += sum(row.encode())
        if n % every == 0:
            await asyncio.sleep(0)  # let other tasks run
    log.append("checksum done")
    return total
