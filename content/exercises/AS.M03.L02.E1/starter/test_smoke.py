import asyncio

import pytest
from fastapi import FastAPI, HTTPException


@pytest.fixture
def anyio_backend():
    return "asyncio"  # run the async tests on asyncio only


def make_app():
    app = FastAPI()
    app.state.in_flight = 0
    app.state.peak = 0
    app.state.hits = []

    async def track():
        app.state.in_flight += 1
        app.state.peak = max(app.state.peak, app.state.in_flight)
        await asyncio.sleep(0.1)
        app.state.in_flight -= 1

    @app.get("/ok/{n}")
    async def ok(n: int):
        app.state.hits.append(n)
        await track()
        return {"n": n}

    @app.get("/missing")
    async def missing():
        await track()
        raise HTTPException(status_code=404)

    @app.get("/crash")
    async def crash():
        await track()
        raise RuntimeError("bug in handler")

    return app


@pytest.mark.anyio
async def test_status_codes():
    from smoke import smoke
    app = make_app()
    result = await smoke(app, ["/ok/1", "/missing", "/nope"], concurrency=3)
    assert result == {"/ok/1": 200, "/missing": 404, "/nope": 404}


@pytest.mark.anyio
async def test_crashing_handler_reports_500():
    from smoke import smoke
    app = make_app()
    result = await smoke(app, ["/crash", "/ok/2"], concurrency=2)
    assert result == {"/crash": 500, "/ok/2": 200}


@pytest.mark.anyio
async def test_concurrency_is_used_and_bounded():
    from smoke import smoke
    app = make_app()
    paths = [f"/ok/{i}" for i in range(10)]
    result = await smoke(app, paths, concurrency=4)
    assert list(result) == paths
    assert app.state.peak == 4, f"peak concurrency was {app.state.peak}, expected exactly 4"


@pytest.mark.anyio
async def test_concurrency_one_is_sequential():
    from smoke import smoke
    app = make_app()
    await smoke(app, ["/ok/1", "/ok/2", "/ok/3"], concurrency=1)
    assert app.state.peak == 1


@pytest.mark.anyio
async def test_duplicates_requested_once():
    from smoke import smoke
    app = make_app()
    result = await smoke(app, ["/ok/7", "/ok/8", "/ok/7"], concurrency=2)
    assert list(result) == ["/ok/7", "/ok/8"]
    assert sorted(app.state.hits) == [7, 8]


@pytest.mark.anyio
async def test_empty_paths():
    from smoke import smoke
    assert await smoke(make_app(), [], concurrency=2) == {}


@pytest.mark.anyio
async def test_bad_concurrency():
    from smoke import smoke
    with pytest.raises(ValueError):
        await smoke(make_app(), ["/ok/1"], concurrency=0)
