"""Two ways to run many async calls when some of them fail (reference solution)."""
import asyncio
from typing import Awaitable, Callable


async def health_report(hosts: list[str], probe: Callable[[str], Awaitable[int]]) -> tuple[dict, dict]:
    """Probe every host concurrently; return (up, down) without letting one failure stop the rest."""
    up, down = {}, {}
    results = await asyncio.gather(*(probe(h) for h in hosts), return_exceptions=True)
    for host, result in zip(hosts, results):
        if isinstance(result, Exception):
            down[host] = result
        else:
            up[host] = result
    return up, down


async def load_settings(names: list[str], fetch: Callable[[str], Awaitable[str]]) -> dict[str, str]:
    """Fetch all settings concurrently; on the first failure cancel the rest and raise an ExceptionGroup."""
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(n)) for n in names]
    return {name: task.result() for name, task in zip(names, tasks)}
