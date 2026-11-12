"""Two async jobs that hog the event loop. Make them cooperate."""
import asyncio  # noqa: F401  (you'll need it)
import time


async def pull_pages(name: str, pages: int, log: list[str]) -> None:
    """Download `pages` pages, appending f"{name}{i}" to log before each one.

    Each page takes about 0.01 s of waiting on the network (simulated here).
    """
    for i in range(pages):
        log.append(f"{name}{i}")
        time.sleep(0.01)  # simulated network wait


async def checksum(rows: list[str], log: list[str], every: int = 100) -> int:
    """Sum of the UTF-8 bytes of all rows. Appends "checksum done" to log at the end.

    Must give other tasks a chance to run after every `every` rows.
    Raises ValueError if every < 1.
    """
    total = 0
    for row in rows:
        total += sum(row.encode())
    log.append("checksum done")
    return total
