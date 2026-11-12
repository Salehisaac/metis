"""Fetch stock quotes from a slow async API (reference solution)."""
import asyncio
from typing import Awaitable, Callable

GetQuote = Callable[[str], Awaitable[float]]


async def fetch_quotes(symbols: list[str], get_quote: GetQuote) -> dict[str, float]:
    """Return {symbol: quote} for each distinct symbol, fetched concurrently."""
    unique = list(dict.fromkeys(symbols))
    async with asyncio.TaskGroup() as tg:
        tasks = {symbol: tg.create_task(get_quote(symbol)) for symbol in unique}
    return {symbol: task.result() for symbol, task in tasks.items()}
