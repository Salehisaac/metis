"""Download many pages without overloading the remote server (reference solution)."""
import asyncio
from typing import Awaitable, Callable


async def fetch_many(urls: list[str], fetch: Callable[[str], Awaitable[str]], limit: int) -> list[str]:
    """Fetch all urls concurrently, at most `limit` at a time; results in input order."""
    if limit < 1:
        raise ValueError("limit must be >= 1")
    sem = asyncio.Semaphore(limit)

    async def one(url: str) -> str:
        async with sem:
            return await fetch(url)

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(one(url)) for url in urls]
    return [t.result() for t in tasks]
