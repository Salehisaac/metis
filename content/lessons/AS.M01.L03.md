---
{
  "id": "AS.M01.L03",
  "title": "Blocking calls and CPU work: asyncio.to_thread and executors",
  "difficulty": "intermediate",
  "minutes": 90,
  "prerequisites": ["AS.M01.L02"],
  "objectives": [
    "Run a blocking sync call with asyncio.to_thread and show (with a heartbeat) that the event loop stays responsive",
    "Explain why to_thread helps blocking I/O but not pure-Python CPU work (the GIL), using a measured comparison",
    "Offload CPU-bound work to a process pool with loop.run_in_executor",
    "Find hidden blocking calls with asyncio debug mode",
    "Choose between an async library, to_thread, a process pool and sleep(0) chunking for a given piece of work"
  ],
  "why": "Most Python libraries you'll meet in backend work (sync SDKs, sqlite3, file I/O, older HTTP clients) block. You can't always swap them for async ones, so you need a safe way to call them from async code, and you need to know when a thread won't help.",
  "applications": [
    "Calling a sync-only SDK (payments, cloud storage, email) from an async FastAPI endpoint",
    "Hashing passwords or resizing images without freezing the server",
    "Finding the one blocking call that makes an async service slow under load"
  ],
  "exercises": ["AS.M01.L03.E1"],
  "sources": [
    {
      "title": "asyncio: Coroutines and Tasks (Running in Threads: to_thread)",
      "url": "https://docs.python.org/3.12/library/asyncio-task.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["asyncio.to_thread runs func in a separate thread (added in 3.9)", "Due to the GIL, to_thread can typically only make IO-bound functions non-blocking"]
    },
    {
      "title": "asyncio: Event Loop (run_in_executor)",
      "url": "https://docs.python.org/3.12/library/asyncio-eventloop.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["run_in_executor arranges for func to be called in the given executor (default executor if None) and returns an asyncio.Future", "The docs example runs a CPU-bound function in a ProcessPoolExecutor"]
    },
    {
      "title": "concurrent.futures: ThreadPoolExecutor and ProcessPoolExecutor",
      "url": "https://docs.python.org/3.12/library/concurrent.futures.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["ThreadPoolExecutor's default max_workers is min(32, os.cpu_count() + 4)", "ProcessPoolExecutor side-steps the GIL; only picklable objects can be executed and returned", "The __main__ module must be importable by worker subprocesses"]
    },
    {
      "title": "Developing with asyncio (debug mode; blocking code)",
      "url": "https://docs.python.org/3.12/library/asyncio-dev.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Debug mode: PYTHONASYNCIODEBUG=1, asyncio.run(debug=True) or loop.set_debug()", "In debug mode callbacks taking longer than 100 ms are logged (loop.slow_callback_duration)", "An executor can run a task in a different thread or process to avoid blocking the event loop's thread"]
    }
  ]
}
---
## 1. Sync libraries: hand the blocking call to a thread

L02 showed that a blocking call inside `async def` freezes everything. Often you can't avoid the call: the SDK you must use is sync-only. The standard answer is `asyncio.to_thread(func, *args)`: it runs `func(*args)` **in a separate worker thread** and returns an awaitable for the result.

```python
import asyncio, threading, time

def legacy_fetch(url):                  # a sync library call, e.g. requests.get
    print(f"  fetching in thread {threading.current_thread().name}")
    time.sleep(1)
    return f"<html of {url}>"

async def heartbeat(start):
    while True:
        print(f"  tick at {time.perf_counter() - start:.1f}s")
        await asyncio.sleep(0.25)

async def main():
    start = time.perf_counter()
    hb = asyncio.create_task(heartbeat(start))
    await asyncio.sleep(0)              # let the heartbeat start
    page = await asyncio.to_thread(legacy_fetch, "example.org")
    print(page, f"after {time.perf_counter() - start:.1f}s")
    print("loop thread:", threading.current_thread().name)
    hb.cancel()

asyncio.run(main())
```

```console
  tick at 0.0s
  fetching in thread asyncio_0
  tick at 0.3s
  tick at 0.5s
  tick at 0.8s
<html of example.org> after 1.0s
loop thread: MainThread
```

The heartbeat keeps ticking during the 1-second blocking call, because the call holds a *worker* thread (`asyncio_0`), not the loop's thread (`MainThread`).

Note what changed compared with L01: **here a thread really is involved, because you asked for one with `to_thread`.** `await` just waits for that thread's result, the same way it waits for a sleep.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import asyncio, threading\n\ndef on_main():\n    return threading.current_thread() is threading.main_thread()\n\nasync def main():\n    print(on_main(), await asyncio.to_thread(on_main))\n\nasyncio.run(main())",
  "answer": "True False",
  "explanation": "Called directly, the function runs on the loop's thread, which is the main thread. Through to_thread it runs in a worker thread." }
```

Return values and exceptions both come back through the `await`, so you handle errors the usual way:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import asyncio\n\ndef parse_port(text):\n    return int(text)\n\nasync def main():\n    try:\n        await asyncio.to_thread(parse_port, \"eighty\")\n    except ValueError:\n        print(\"bad port\")\n    print(await asyncio.to_thread(parse_port, \"8080\") + 1)\n\nasyncio.run(main())",
  "answer": "bad port\n8081",
  "explanation": "The ValueError raised in the worker thread is re-raised at the await, and a successful call's return value is the await's value." }
```

## 2. Threads don't speed up Python CPU work (the GIL)

In Go, two CPU-heavy goroutines use two cores. In CPython, the **GIL** (global interpreter lock) lets only one thread run Python bytecode at a time. The docs say it plainly: due to the GIL, `to_thread` can typically only be used to make **I/O-bound** functions non-blocking. Measured on this machine (20 CPU cores), the same pure-Python function twice:

```python
import asyncio, time

def crunch(n):
    return sum(i * i for i in range(n))

async def main():
    n = 20_000_000
    t = time.perf_counter()
    crunch(n); crunch(n)
    print(f"sequential:      {time.perf_counter() - t:.2f}s")
    t = time.perf_counter()
    a = asyncio.create_task(asyncio.to_thread(crunch, n))
    b = asyncio.create_task(asyncio.to_thread(crunch, n))
    await a; await b
    print(f"two to_thread:   {time.perf_counter() - t:.2f}s")

asyncio.run(main())
```

```console
sequential:      0.90s
two to_thread:   1.36s
```

Two threads were *slower* than doing it one after the other: they took turns holding the GIL and paid for the switching. (A thread still keeps the loop responsive while it runs; it just doesn't add CPU power.)

For CPU-bound work, use **processes**, each with its own interpreter and its own GIL. `loop.run_in_executor(executor, func, *args)` runs a function in any `concurrent.futures` executor; the docs' own example uses a `ProcessPoolExecutor` for a CPU-bound function:

```python
import asyncio, time
from concurrent.futures import ProcessPoolExecutor

def crunch(n):
    return sum(i * i for i in range(n))

async def main():
    n = 20_000_000
    loop = asyncio.get_running_loop()
    t = time.perf_counter()
    with ProcessPoolExecutor() as pool:
        a = loop.run_in_executor(pool, crunch, n)
        b = loop.run_in_executor(pool, crunch, n)
        await a; await b
    print(f"two processes:   {time.perf_counter() - t:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
```

```console
two processes:   0.52s
```

0.52 s for both, including starting the worker processes. The price: arguments and results must be picklable and are copied between processes, so this pays off for big computations on small inputs, not for many tiny calls. The `if __name__ == "__main__":` guard (PY.M01) is required here: the docs say the `__main__` module must be importable by the worker processes.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "Running two pure-Python CPU-bound calls with `asyncio.to_thread` at the same time makes them finish in about half the time of running them one after the other.", "answer": false,
  "explanation": "The GIL lets one thread run Python bytecode at a time. Measured above: 1.36 s with two threads vs 0.90 s sequential. Use a process pool for CPU work." }
```

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "An async service must compute a 2-second pure-Python report without freezing other requests, and the machine has idle cores. Which option uses those cores?",
  "options": ["Call the function directly inside async def", "await asyncio.to_thread(report)", "await loop.run_in_executor(process_pool, report)", "Add await asyncio.sleep(0) before calling it"], "answer": 2,
  "explanation": "A process has its own GIL, so the work runs in parallel on another core and the loop stays free. to_thread keeps the loop responsive but competes for the GIL; sleep(0) before the call changes nothing." }
```

## 3. Finding the hidden blocker: debug mode

Blocking calls hide inside helper functions and libraries. asyncio's **debug mode** reports them: enable it with `PYTHONASYNCIODEBUG=1`, `asyncio.run(main(), debug=True)` or `loop.set_debug()`, and any step that holds the loop longer than 100 ms is logged (`loop.slow_callback_duration` sets the threshold).

```python
import asyncio, time

async def handler():
    time.sleep(0.3)        # blocking call hidden in async code

asyncio.run(handler(), debug=True)
```

```console
Executing <Task finished name='Task-1' coro=<handler() done, defined at .../m3d.py:3> result=None created at /usr/lib/python3.12/asyncio/runners.py:100> took 0.301 seconds
```

"took 0.301 seconds" for one task step means that step never gave the loop back. Turn debug mode on in development and in your async tests, not in production (it slows things down).

## 4. Choosing the tool

| The slow part is... | Use | Why |
|---|---|---|
| I/O, and an async library exists (httpx, aiosqlite, async Redis) | `await` the async library | No threads at all; scales to many waits |
| I/O through a sync-only library | `await asyncio.to_thread(func, ...)` | The wait happens in a worker thread |
| Heavy pure-Python CPU work | `loop.run_in_executor(ProcessPoolExecutor(), ...)` | Its own process, its own GIL, another core |
| A moderate loop you control | `await asyncio.sleep(0)` every N items | Lets others run; no threads or processes |

Common mistakes:

- **`await asyncio.to_thread(func())`** with parentheses: that calls `func` right now, on the loop's thread, and passes its *result* to `to_thread`. Pass the function and its arguments separately: `to_thread(func, arg)`.
- **Using asyncio primitives inside the thread.** Code running via `to_thread` is in another thread: `asyncio.Lock` and friends are not thread-safe. Keep the thread function plain and sync.
- **Thinking `to_thread` is free.** In CPython 3.12 `to_thread` hands the call to the loop's default executor, a `ThreadPoolExecutor` (that's why the thread above is named `asyncio_0`). The docs give `ThreadPoolExecutor`'s default size as `min(32, os.cpu_count() + 4)`, and on this machine (20 cores) the loop's default executor reported 24 workers after one `to_thread` call. So a thousand concurrent `to_thread` calls mostly wait in a queue. Bound your concurrency instead (AS.M02.L04).

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "An endpoint has `data = await asyncio.to_thread(s3_client.download(key))` and the server still freezes during downloads. Why?",
  "options": ["to_thread only works for CPU-bound code", "`s3_client.download(key)` runs immediately on the loop's thread; its result, not the function, is passed to to_thread", "to_thread must be wrapped in create_task", "The S3 client needs the GIL"], "answer": 1,
  "explanation": "Arguments are evaluated before the call. Write to_thread(s3_client.download, key) so the call itself happens in the worker thread." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Your async API calls a sync payment SDK (about 300 ms per call, mostly waiting on the network) and also computes a bcrypt password hash (about 250 ms of CPU). Which tool would you use for each, and why?",
  "model": "The payment SDK call is I/O-bound and sync-only: run it with await asyncio.to_thread(sdk.charge, ...), so the waiting happens in a worker thread and the loop serves other requests. The hash is CPU-bound: run it in a process pool via loop.run_in_executor, or use to_thread only if the hashing library releases the GIL (the docs allow to_thread for CPU work in extension modules that release it). Calling either directly in async def would freeze all requests for that time.",
  "explanation": "I/O-bound sync call → to_thread. CPU-bound Python → process pool (or to_thread if the extension releases the GIL)." }
```

## 5. Your turn

The exercise gives you a sync-only geocoding client and an async function that calls it directly. Make the calls run in worker threads, and stop geocoding the same city twice. The tests run a heartbeat next to your code and record which thread each call ran on.

```exercise
AS.M01.L03.E1
```
