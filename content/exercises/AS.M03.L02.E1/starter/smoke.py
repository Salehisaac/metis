"""A smoke tester: hit many paths of an ASGI app concurrently and collect the status codes."""
from fastapi import FastAPI


async def smoke(app: FastAPI, paths: list[str], concurrency: int) -> dict[str, int]:
    """GET every path of `app` in-process (no network, no server) and return {path: status_code}.

    - Use one httpx.AsyncClient for all requests, wired to the app with httpx.ASGITransport.
    - Run the requests concurrently, but at most `concurrency` at a time.
    - A handler that raises must show up as status 500, not as an exception.
    - Keys follow the order of `paths`; a path that appears twice is requested once.
    - Raise ValueError if concurrency < 1.
    """
    raise NotImplementedError
