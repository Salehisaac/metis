"""A smoke tester: hit many paths of an ASGI app concurrently (reference solution)."""
import asyncio

import httpx
from fastapi import FastAPI


async def smoke(app: FastAPI, paths: list[str], concurrency: int) -> dict[str, int]:
    """GET every distinct path in-process, at most `concurrency` at a time; return {path: status}."""
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    unique = list(dict.fromkeys(paths))
    limit = asyncio.Semaphore(concurrency)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        async def status(path: str) -> int:
            async with limit:
                response = await client.get(path)
                return response.status_code

        codes = await asyncio.gather(*(status(p) for p in unique))
    return dict(zip(unique, codes))
