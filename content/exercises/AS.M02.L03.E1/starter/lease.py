"""Run queries on pooled connections, with a deadline. Fix the bugs in run_query and query_or_default."""
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
    result = await run(conn, query)
    pool.release(conn)
    return result


async def query_or_default(pool: Pool, query: str, run: Runner, seconds: float, default: Any = None) -> Any:
    """Like run_query, but give up after `seconds` and return `default` instead.

    Errors from the query propagate. If the calling task is cancelled, the cancellation
    must propagate too: it is not a timeout.
    """
    try:
        return await run_query(pool, query, run)
    except asyncio.CancelledError:
        return default
