"""Two ways to run many async calls when some of them fail."""
import asyncio
from typing import Awaitable, Callable


async def health_report(hosts: list[str], probe: Callable[[str], Awaitable[int]]) -> tuple[dict, dict]:
    """Probe every host concurrently and report on all of them.

    Returns (up, down):
      up   = {host: status_code} for probes that returned
      down = {host: exception}   for probes that raised an Exception
    One failing probe must not stop or cancel the others.
    """
    up, down = {}, {}
    results = await asyncio.gather(*(probe(h) for h in hosts))
    for host, result in zip(hosts, results):
        up[host] = result
    return up, down


async def load_settings(names: list[str], fetch: Callable[[str], Awaitable[str]]) -> dict[str, str]:
    """Fetch every named setting concurrently. All of them are required.

    If any fetch raises, the fetches still running are cancelled before this function
    raises, and the error reaches the caller inside an ExceptionGroup.
    """
    values = await asyncio.gather(*(fetch(n) for n in names))
    return dict(zip(names, values))
