"""Run queries on pooled connections, with a deadline (reference solution)."""
import asyncio
from typing import Any, Awaitable, Callable

Runner = Callable[[str, str], Awaitable[Any]]


class Pool:
    """A tiny connection pool that counts leased connections. Correct, don't change."""

    def __init__(self):
        self.leased = 0
        self._next = 0

    def acquire(self) -> str:
        self.leased += 1
        self._next += 1
        return f"conn-{self._next}"

    def release(self, conn: str) -> None:
        self.leased -= 1


async def run_query(pool: Pool, query: str, run: Runner) -> Any:
    """Lease a connection, run the query on it, and always give the connection back."""
    conn = pool.acquire()
    try:
        return await run(conn, query)
    finally:
        pool.release(conn)


async def query_or_default(pool: Pool, query: str, run: Runner, seconds: float, default: Any = None) -> Any:
    """Like run_query, but give up after `seconds` and return `default` instead."""
    try:
        async with asyncio.timeout(seconds):
            return await run_query(pool, query, run)
    except TimeoutError:
        return default
