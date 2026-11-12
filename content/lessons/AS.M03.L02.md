---
{
  "id": "AS.M03.L02",
  "title": "Testing async apps: AnyIO pytest plugin and httpx.AsyncClient",
  "difficulty": "intermediate",
  "minutes": 80,
  "prerequisites": ["AS.M03.L01"],
  "objectives": [
    "Write async test functions with @pytest.mark.anyio and pin the backend with an anyio_backend fixture",
    "Send requests to a FastAPI app in-process with httpx.AsyncClient and httpx.ASGITransport, and await other async code in the same test",
    "Explain what raise_app_exceptions changes and that AsyncClient does not run lifespan events",
    "Test concurrency deterministically with counters and barriers instead of timing assertions"
  ],
  "why": "Once your app, your fakes and your database helpers are async, your tests need to await too. TestClient is sync, so it's the wrong tool inside an async test. The AnyIO plugin plus httpx.AsyncClient is the setup FastAPI's own docs use, and it is already installed here, no pytest-asyncio needed.",
  "applications": [
    "Testing async endpoints and then checking the database with async queries in the same test",
    "Testing that endpoints really run concurrently (the AS.M03.L01 exercise's barrier test)",
    "Reusing one httpx client code path for in-process tests and real smoke tests against staging"
  ],
  "exercises": ["AS.M03.L02.E1"],
  "sources": [
    {
      "title": "FastAPI docs: Async Tests",
      "url": "https://fastapi.tiangolo.com/advanced/async-tests/",
      "version": "FastAPI docs (page states no version; installed fastapi 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["@pytest.mark.anyio tells pytest the test function should be called asynchronously", "Create an AsyncClient with transport=ASGITransport(app=app) and base_url, and send requests with await", "When running tests asynchronously you can no longer use TestClient inside the test functions", "AsyncClient won't trigger lifespan events; the docs suggest LifespanManager from asgi-lifespan", "Instantiate objects that need an event loop only within async functions"]
    },
    {
      "title": "AnyIO: Testing with AnyIO (pytest plugin)",
      "url": "https://anyio.readthedocs.io/en/stable/testing.html",
      "version": "AnyIO stable docs (installed anyio 4.16.0)",
      "verified": "2026-11-12",
      "claims": ["AnyIO ships a pytest plugin; the marker @pytest.mark.anyio only affects async test functions", "Define an anyio_backend fixture to choose the backend", "The plugin supports coroutine functions as fixtures when used by AnyIO-enabled tests"]
    },
    {
      "title": "HTTPX: Transports (ASGI transport)",
      "url": "https://www.python-httpx.org/advanced/transports/",
      "version": "HTTPX docs (installed httpx 0.28.1)",
      "verified": "2026-11-12",
      "claims": ["ASGITransport(app=app) is used with AsyncClient(transport=..., base_url=...)", "raise_app_exceptions=False lets you inspect 500 error responses rather than raise exceptions"]
    }
  ]
}
---
## 1. Why not just TestClient?

In WEB.M04 you tested endpoints with `TestClient` from plain `def` tests. It hides the event loop: you call `client.get(...)` and it runs the async app for you. That's fine until the **test itself** needs to `await` something:

- check the database afterwards with an async query (L03),
- call an async fake or an async helper,
- send several requests *concurrently* to prove they overlap (the AS.M03.L01 exercise).

Then the test function must be `async def`. The FastAPI docs say that inside async test functions you can no longer use `TestClient`; use `httpx.AsyncClient` instead. (A quick `TestClient` call inside an async test happened to work on this machine, but it's a sync call: it blocks the test's event loop until it returns, so you can't overlap requests with it. Don't mix them.)

## 2. Async tests with the AnyIO plugin

pytest itself can't run `async def` tests. If you forget the marker, you get this (real output, pytest 9.2.0):

```console
async def functions are not natively supported.
You need to install a suitable plugin for your async framework, for example:
  - anyio
  - pytest-asyncio
  ...
FAILED test_tc.py::test_forgot_marker - Failed: async def functions are not n...
```

AnyIO, the async library under Starlette and FastAPI, ships a pytest plugin, already installed here. Mark the test with `@pytest.mark.anyio` and it is run inside an event loop. Here's a small app and its tests:

```python
# greet_app.py
import asyncio
from fastapi import FastAPI

app = FastAPI()
greetings: list[str] = []


async def translate(name: str) -> str:      # pretend this calls a translation service
    await asyncio.sleep(0.01)
    return f"Salam, {name}"


@app.post("/greet/{name}", status_code=201)
async def greet(name: str):
    text = await translate(name)
    greetings.append(text)
    return {"text": text}
```

```python
# test_greet.py
import httpx
import pytest

import greet_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=greet_app.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_greet(client):
    greet_app.greetings.clear()
    response = await client.post("/greet/Sara")
    assert response.status_code == 201
    assert response.json() == {"text": "Salam, Sara"}
    assert greet_app.greetings == ["Salam, Sara"]


@pytest.mark.anyio
async def test_translate_directly():
    assert await greet_app.translate("Ali") == "Salam, Ali"
```

```console
$ pytest -v
test_greet.py::test_greet PASSED                                         [ 50%]
test_greet.py::test_translate_directly PASSED                            [100%]
============================== 2 passed in 0.15s ===============================
```

Three pieces:

- **`@pytest.mark.anyio`** on each async test (or on the module with `pytestmark = pytest.mark.anyio`).
- **The `anyio_backend` fixture** picks the event loop implementation. AnyIO supports asyncio and Trio. Without this fixture the plugin chooses the backends itself (on this machine, with Trio not installed, only `[asyncio]` ran). Pinning `"asyncio"` makes the runs the same everywhere. Put it in `conftest.py` for a whole project.
- **Async fixtures.** The plugin also runs `async def` fixtures, including `yield` ones, for AnyIO tests. Here the fixture opens the client and closes it after the test.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "You write `async def test_signup(): ...` without any marker, in this academy's setup (AnyIO plugin, no pytest-asyncio). What happens when you run pytest?",
  "options": ["The test passes without running its body", "The test fails with 'async def functions are not natively supported'", "pytest runs it with asyncio automatically", "It is collected as a fixture"], "answer": 1,
  "explanation": "pytest can't await a coroutine by itself. With @pytest.mark.anyio, the AnyIO plugin runs the test in an event loop." }
```

## 3. `AsyncClient` + `ASGITransport`

`httpx.ASGITransport(app=app)` makes `AsyncClient` call your app object **directly, in the same event loop**: no server, no socket, no port. `base_url` is needed so relative paths form full URLs; the host name doesn't matter.

Two behaviours to know:

**Handler exceptions are re-raised by default.** That's what you want in most tests, because you get the real traceback instead of a bare 500. To see the 500 the way a client would, set `raise_app_exceptions=False`:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print? (installed httpx 0.28.1, fastapi 0.162.0)",
  "code": "import asyncio\nimport httpx\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get(\"/divide/{a}/{b}\")\nasync def divide(a: int, b: int):\n    return {\"result\": a // b}\n\nasync def main():\n    strict = httpx.ASGITransport(app=app)\n    async with httpx.AsyncClient(transport=strict, base_url=\"http://test\") as client:\n        try:\n            await client.get(\"/divide/1/0\")\n        except ZeroDivisionError:\n            print(\"raised ZeroDivisionError\")\n    lenient = httpx.ASGITransport(app=app, raise_app_exceptions=False)\n    async with httpx.AsyncClient(transport=lenient, base_url=\"http://test\") as client:\n        r = await client.get(\"/divide/1/0\")\n        print(r.status_code)\n\nasyncio.run(main())",
  "answer": "raised ZeroDivisionError\n500",
  "explanation": "By default ASGITransport re-raises the handler's exception in the test. With raise_app_exceptions=False you get the 500 response instead." }
```

**Lifespan events don't run.** The FastAPI docs say `AsyncClient` won't trigger lifespan events (they suggest `LifespanManager` from the `asgi-lifespan` package, which is not installed here). Checked on this machine: a lifespan that appends `"startup"` to a list left the list empty after requests through `AsyncClient`. So don't hide test setup (creating tables, connecting clients) in lifespan; do it in a fixture, or in the app's dependencies.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "Requests sent with `httpx.AsyncClient(transport=httpx.ASGITransport(app=app), ...)` run the app's lifespan startup code first.", "answer": false,
  "explanation": "The FastAPI docs: AsyncClient won't trigger lifespan events. Set up what the test needs in a fixture." }
```

One more tip from the FastAPI docs: if you hit `RuntimeError: ... attached to a different loop`, create objects that need an event loop (clients, connections) **inside** async functions or fixtures, not at import time.

## 4. Test concurrency without timing

A test like `assert elapsed < 0.3` passes on your laptop and fails on a busy CI runner. To prove that things run concurrently, measure **overlap**, not speed:

- **A counter of calls in flight.** Increment on entry, decrement on exit, record the peak (AS.M02.L04). `peak == 4` is exact and doesn't depend on machine speed.
- **A barrier.** A fake that only returns when N calls are waiting at the same time (`threading.Barrier(N, timeout=1)` for code that runs in threads). If the calls can't overlap, the barrier times out and the test fails with a clear error instead of hanging.
- **A bound on every test.** Wrap anything that might hang in `asyncio.timeout(...)` (or AnyIO's `fail_after`) so a broken implementation fails fast.

Timing still has a place in benchmarks and in this academy's lessons ("measured on this machine"). In assertions, use generous bounds at most.

```quiz
{ "id": "q4", "type": "choice", "label": "Application",
  "prompt": "You want a test that proves `fetch_all` runs 5 downloads concurrently. Which assertion is the most reliable on a slow, shared CI machine?",
  "options": ["The total time is under 0.25 s when each fake download sleeps 0.2 s", "The fake download's in-flight counter reached a peak of 5", "The results come back in a different order than the inputs", "No exception was raised"], "answer": 1,
  "explanation": "The peak counter measures overlap directly and doesn't depend on machine speed. The timing bound can fail on a busy runner; order and 'no exception' don't prove concurrency." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Application",
  "prompt": "A teammate's async test suite sometimes fails with 'attached to a different loop', and their tests create an async Redis client at module import time. They also assert `elapsed < 0.1` in several tests. What two changes do you suggest?",
  "model": "Create loop-bound objects inside async fixtures (or inside the test), so each is created on the loop that uses it, as the FastAPI docs advise; close them in the fixture's teardown. Replace elapsed-time assertions with overlap measurements (peak in-flight counters, barriers) and bound each test with asyncio.timeout so failures are fast and deterministic.",
  "explanation": "Create loop-bound objects on the right loop; measure overlap, not time." }
```

## 5. Your turn

Write `smoke()`, an in-process smoke tester: it sends GET requests to a FastAPI app through `AsyncClient` + `ASGITransport`, bounded by a semaphore, and reports status codes, including 500 for crashing handlers. The tests are AnyIO tests; read them as a second worked example of this lesson.

```exercise
AS.M03.L02.E1
```
