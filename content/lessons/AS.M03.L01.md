---
{
  "id": "AS.M03.L01",
  "title": "async def vs def endpoints: the threadpool and the blocked loop",
  "difficulty": "intermediate",
  "minutes": 90,
  "prerequisites": ["AS.M02", "WEB.M05"],
  "objectives": [
    "Explain where FastAPI runs an async def endpoint (on the event loop) and a def endpoint (in a threadpool), and show it by printing thread names",
    "Predict the latency of N concurrent requests for async def with a blocking call, def with a blocking call, and async def with a real await, and confirm it by measurement",
    "Choose async def, def, or async def plus asyncio.to_thread for an endpoint, based on the libraries it calls",
    "Name the threadpool's limit and what happens when it is exhausted"
  ],
  "why": "This is where AS.M01 and AS.M02 meet your daily FastAPI work. The single most common async performance bug in FastAPI code is a blocking call inside an async def endpoint: it works perfectly in a one-user test and collapses under load. The fix is usually one keyword or one to_thread call, if you know which.",
  "applications": [
    "Deciding async def vs def for every endpoint and dependency you write",
    "Reviewing pull requests for requests.get, time.sleep, sync DB sessions or heavy CPU inside async def",
    "Explaining a latency spike that only appears under concurrent load"
  ],
  "exercises": ["AS.M03.L01.E1"],
  "sources": [
    {
      "title": "FastAPI docs: Concurrency and async / await",
      "url": "https://fastapi.tiangolo.com/async/",
      "version": "FastAPI docs (page states no version; installed fastapi 0.162.0, starlette 1.10.0)",
      "verified": "2026-11-12",
      "claims": ["A def path operation is run in an external threadpool that is then awaited, instead of being called directly (as it would block the server)", "Use def when a library doesn't support await; use async def when you only call awaitable things or nothing at all", "If you just don't know, use normal def", "def dependencies are also run in the external threadpool", "You can only use await inside functions created with async def"]
    },
    {
      "title": "AnyIO: Working with threads (default capacity limiter)",
      "url": "https://anyio.readthedocs.io/en/stable/threads.html",
      "version": "AnyIO stable docs (installed anyio 4.16.0)",
      "verified": "2026-11-12",
      "claims": ["The default AnyIO worker thread limiter has a value of 40", "It can be changed via to_thread.current_default_thread_limiter().total_tokens"]
    },
    {
      "title": "HTTPX: Transports (ASGI transport)",
      "url": "https://www.python-httpx.org/advanced/transports/",
      "version": "HTTPX docs (installed httpx 0.28.1)",
      "verified": "2026-11-12",
      "claims": ["httpx.ASGITransport(app=app) with AsyncClient(transport=..., base_url=...) calls directly into an ASGI app", "raise_app_exceptions=False lets you inspect 500 responses instead of raising"]
    },
    {
      "title": "asyncio: Coroutines and Tasks (to_thread)",
      "url": "https://docs.python.org/3.12/library/asyncio-task.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["asyncio.to_thread runs a function in a separate thread"]
    }
  ]
}
---
## 1. Two kinds of endpoints, two places to run

You know from AS.M01 that an event loop runs on one thread and a blocking call there stops everything. FastAPI runs on an event loop too, and it treats your two kinds of path operation functions differently. The FastAPI docs:

- **`async def`**: called directly on the event loop. It must only *wait* by awaiting.
- **`def`**: "run in an external threadpool that is then awaited, instead of being called directly (as it would block the server)". Dependencies declared with `def` are run in the threadpool too.

See it for yourself. (`AsyncClient` with `ASGITransport` sends requests straight into the app without a network; L02 covers it.)

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print? (installed fastapi 0.162.0)",
  "code": "import asyncio, threading\nfrom fastapi import FastAPI\nfrom httpx import ASGITransport, AsyncClient\n\napp = FastAPI()\n\n@app.get(\"/a\")\nasync def on_loop():\n    return threading.current_thread().name\n\n@app.get(\"/s\")\ndef in_pool():\n    return threading.current_thread().name\n\nasync def main():\n    async with AsyncClient(transport=ASGITransport(app=app), base_url=\"http://test\") as client:\n        print((await client.get(\"/a\")).json())\n        print((await client.get(\"/s\")).json())\n\nasyncio.run(main())",
  "answer": "MainThread\nAnyIO worker thread",
  "explanation": "The async def endpoint runs on the event loop's thread (here the main thread). The def endpoint runs in a worker thread from the threadpool FastAPI uses (provided by AnyIO, hence the name)." }
```

## 2. Measured: what blocks and what doesn't

Four endpoints, each with 0.2 s of waiting, five concurrent requests to each. Measured on this machine:

```python
import asyncio, threading, time
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

app = FastAPI()

def slow_sdk_call():                 # a sync library call: blocks its thread for 0.2 s
    time.sleep(0.2)

@app.get("/async-blocking")
async def async_blocking():
    slow_sdk_call()                  # blocks the event loop
    return {"thread": threading.current_thread().name}

@app.get("/def-blocking")
def def_blocking():
    slow_sdk_call()                  # blocks a threadpool worker only
    return {"thread": threading.current_thread().name}

@app.get("/async-awaiting")
async def async_awaiting():
    await asyncio.sleep(0.2)         # a real async wait
    return {"thread": threading.current_thread().name}

@app.get("/async-to-thread")
async def async_to_thread():
    await asyncio.to_thread(slow_sdk_call)
    return {"thread": threading.current_thread().name}

async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in ("/async-blocking", "/def-blocking", "/async-awaiting", "/async-to-thread"):
            t = time.perf_counter()
            responses = await asyncio.gather(*(client.get(path) for _ in range(5)))
            print(f"{path:17} 5 requests: {time.perf_counter() - t:.2f}s  ran on: {responses[0].json()['thread']}")

asyncio.run(main())
```

```console
/async-blocking   5 requests: 1.01s  ran on: MainThread
/def-blocking     5 requests: 0.22s  ran on: AnyIO worker thread
/async-awaiting   5 requests: 0.21s  ran on: MainThread
/async-to-thread  5 requests: 0.21s  ran on: MainThread
```

- **`async def` + blocking call: 1.01 s.** The five requests were served one after another, because each one held the loop for 0.2 s. With 100 users that's 20 s for the last one, and every other endpoint of the app is frozen meanwhile.
- **`def` + blocking call: 0.22 s.** Five worker threads blocked in parallel; the loop stayed free.
- **`async def` + `await`: 0.21 s.** No threads at all; the waits overlapped on the loop.
- **`async def` + `to_thread`: 0.21 s.** The blocking part went to a thread; the endpoint itself stayed on the loop and could still `await` other things.

So `async def` is *not* "the fast option". It's faster only when everything that waits inside it is awaited. Otherwise it's the slowest option.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "An `async def` endpoint calls `requests.get(url)` (a sync HTTP client) that takes 1 s. Ten users call it at the same moment. Roughly when does the last one get a response?",
  "options": ["After about 1 s", "After about 10 s", "After about 0.1 s", "Immediately; requests.get runs in a thread automatically"], "answer": 1,
  "explanation": "requests.get blocks the event loop's thread, and async def endpoints run on that thread, so the ten requests are served one at a time: about 10 s for the last. As def (threadpool) it would be about 1 s." }
```

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "Declaring an endpoint with `async def` makes the blocking calls inside it run concurrently with other requests.", "answer": false,
  "explanation": "async def only means FastAPI calls it on the event loop. Blocking calls inside it block the loop. Concurrency comes from awaiting, from def (threadpool), or from to_thread." }
```

## 3. Choosing

| The endpoint (or dependency) calls... | Declare it | Why |
|---|---|---|
| Only async libraries (`await httpx.AsyncClient`, aiosqlite, async Redis), or nothing that waits | `async def` | Runs on the loop, no thread needed |
| Sync libraries that block (requests, a sync DB session, a sync SDK) and nothing async | `def` | FastAPI puts it in the threadpool |
| Both: something async **and** a blocking call | `async def` + `await asyncio.to_thread(blocking, ...)` | You need `await`, so it must be async; move only the blocking part |
| Heavy CPU work | either, plus a process pool (AS.M01.L03) | Threads don't add CPU because of the GIL |

The FastAPI docs' own advice when unsure: **"If you just don't know, use normal `def`."** A wrongly chosen `def` costs a thread; a wrongly chosen `async def` blocks everyone.

Common mistakes:

- **A sync DB session in an `async def` endpoint.** If WEB.M05 gave you a sync SQLAlchemy `Session` (or `sqlite3`), its queries block. Either keep those endpoints `def`, or switch to an async driver (L03).
- **`asyncio.run(...)` inside a `def` endpoint** to call an async function. That starts a whole new event loop per request in a worker thread. If you need to await, make the endpoint `async def`.
- **Forgetting dependencies.** A `def` dependency (say, one that opens a sync DB connection) runs in the threadpool; an `async def` dependency runs on the loop and has the same rules as endpoints.

```quiz
{ "id": "q4", "type": "choice", "label": "Application",
  "prompt": "An endpoint must `await cache.get(key)` (async Redis client) and, on a miss, call `legacy_pricing.compute(key)`, a sync function that does a blocking network call. How should you write it?",
  "options": ["def endpoint; call both directly", "async def endpoint; await the cache, then `await asyncio.to_thread(legacy_pricing.compute, key)`", "async def endpoint; call legacy_pricing.compute(key) directly", "def endpoint; `asyncio.run(cache.get(key))`, then compute"], "answer": 1,
  "explanation": "It needs await, so it must be async def; the blocking call then goes to a thread with to_thread. A def endpoint can't await, and asyncio.run per request is wrong." }
```

## 4. The threadpool has a size

The worker threads come from AnyIO, the async library under Starlette and FastAPI (that's the `AnyIO worker thread` name). The AnyIO docs say its default worker thread limiter has a value of 40; on this machine `anyio.to_thread.current_default_thread_limiter().total_tokens` reports `40`. So if 41 requests are blocked in `def` endpoints at once, the 41st waits for a free thread, even though the event loop itself is idle.

That's the real trade-off: `def` scales to "number of threads" concurrent blocking calls, while proper `async def` with async libraries scales to thousands of concurrent waits (AS.M02.L01). For most CRUD apps 40 is plenty. For an endpoint that waits on slow upstream services under heavy load, an async client is worth it.

```quiz
{ "id": "q5", "type": "explain", "label": "Debugging",
  "prompt": "A FastAPI service is fast in local testing but p99 latency explodes under load, for all endpoints, even /health. One endpoint is `async def export(): data = s3.get_object(...)` using the sync boto3 client. Explain the cause and give two fixes.",
  "model": "boto3 is sync, so get_object blocks the event loop's thread while waiting for S3. Since async def endpoints (and /health) all run on that loop, every request waits behind each export call. Fix: declare export as def so it runs in the threadpool, or keep async def and call await asyncio.to_thread(s3.get_object, ...). Longer term, an async S3 client.",
  "explanation": "One blocking call in async def slows down the whole app, not just that endpoint." }
```

## 5. Your turn

The exercise is a shipping-quote API whose two `async def` endpoints call a sync carrier SDK directly. One endpoint only does blocking work, the other also has to await an async call, so they need different fixes. The tests replace the SDK with a fake that only answers when two requests are inside it at the same time: if the loop is blocked, that can never happen.

```exercise
AS.M03.L01.E1
```
