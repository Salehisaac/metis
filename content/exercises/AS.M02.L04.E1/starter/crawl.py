"""Download many pages without overloading the remote server."""
from typing import Awaitable, Callable


async def fetch_many(urls: list[str], fetch: Callable[[str], Awaitable[str]], limit: int) -> list[str]:
    """Return [await fetch(url) for url in urls], in input order.

    Run the fetches concurrently, but never more than `limit` at the same time.
    Raise ValueError if limit < 1. If a fetch raises, the error propagates (wrapped in an
    ExceptionGroup is fine).
    """
    raise NotImplementedError
