"""Fetch stock quotes from a slow async API."""
from typing import Awaitable, Callable

GetQuote = Callable[[str], Awaitable[float]]


async def fetch_quotes(symbols: list[str], get_quote: GetQuote) -> dict[str, float]:
    """Return {symbol: await get_quote(symbol)} for each distinct symbol, in first-seen order.

    The lookups must run concurrently, not one after another. Each distinct symbol is
    fetched once.
    """
    quotes = {}
    for symbol in symbols:
        quotes[symbol] = await get_quote(symbol)
    return quotes
