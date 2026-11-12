---
{
  "id": "AS.M02.L03",
  "title": "Timeouts and cancellation",
  "difficulty": "intermediate",
  "minutes": 100,
  "prerequisites": ["AS.M02.L02"],
  "objectives": [
    "Put a deadline on async work with asyncio.timeout (3.11+) or wait_for, and catch TimeoutError in the right place",
    "Explain how cancellation is delivered (CancelledError at the suspended await) and predict the order of cleanup output",
    "Write cleanup that runs on success, error and cancellation using try/finally",
    "Explain why swallowing CancelledError breaks timeouts and task groups, and re-raise it when catching it"
  ],
  "why": "Every network call needs a deadline, and every request can be abandoned: a client disconnects, a sibling task fails, a timeout fires. In Go you thread ctx through every call and check ctx.Done(). In asyncio cancellation arrives on its own as an exception, which is convenient, but only if your code lets it through and cleans up.",
  "applications": [
    "Deadlines on calls to slow downstream services, with a fallback value",
    "Releasing connections, locks and temp files when a request is cancelled",
    "Reviewing code for `except Exception` / `except CancelledError` blocks that hide cancellations"
  ],
  "exercises": ["AS.M02.L03.E1"],
  "sources": [
    {
      "title": "asyncio: Coroutines and Tasks (timeouts, cancellation)",
      "url": "https://docs.python.org/3.12/library/asyncio-task.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["asyncio.timeout was added in 3.11; on expiry it cancels the current task and transforms the CancelledError into TimeoutError, which can only be caught outside the context manager", "asyncio.timeout(None) applies no limit; Timeout.reschedule() can change the deadline", "wait_for cancels the task and raises TimeoutError on timeout (TimeoutError instead of asyncio.TimeoutError since 3.11)", "Task.cancel() requests cancellation; CancelledError is raised in the task at the next opportunity", "Use try/finally for clean-up; if CancelledError is caught it should generally be propagated after clean-up", "Suppressing cancellation is actively discouraged; it would also require Task.uncancel()", "shield() protects an awaitable from being cancelled, but the caller still gets CancelledError"]
    },
    {
      "title": "asyncio: Exceptions",
      "url": "https://docs.python.org/3.12/library/asyncio-exceptions.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["CancelledError can be caught to perform custom operations; in almost all situations it must be re-raised", "Since 3.8 CancelledError is a subclass of BaseException rather than Exception", "asyncio.TimeoutError is a deprecated alias of TimeoutError since 3.11"]
    },
    {
      "title": "Python Tutorial: Errors and Exceptions",
      "url": "https://docs.python.org/3.12/tutorial/errors.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["ExceptionGroup wraps several exceptions; except* handles the matching ones"]
    }
  ]
}
---
## 1. Deadlines: `asyncio.timeout`

Go: `ctx, cancel := context.WithTimeout(ctx, 500*time.Millisecond)`, pass `ctx` into every call, check the error. Python 3.11+: wrap the awaits in `async with asyncio.timeout(seconds):`. Measured on this machine:

```python
import asyncio, time

async def slow_report():
    await asyncio.sleep(2)
    return "report"

async def main():
    t = time.perf_counter()
    try:
        async with asyncio.timeout(0.5):
            result = await slow_report()
    except TimeoutError:
        result = "cached report"
    print(result, f"after {time.perf_counter() - t:.2f}s")

asyncio.run(main())
```

```console
cached report after 0.50s
```

How it works, per the docs: when the deadline passes, the context manager **cancels the current task**, catches the resulting `CancelledError` when it reaches the `async with`, and raises **`TimeoutError`** instead. Consequences:

- Catch `TimeoutError` **outside** the `async with` block. Inside it, the in-flight `await` sees a `CancelledError`, not a `TimeoutError`.
- One deadline covers every await in the block: three calls inside share 0.5 s in total.
- `asyncio.timeout(None)` means no limit, and `.reschedule()` can change the deadline.

The older form, `await asyncio.wait_for(slow_report(), timeout=0.5)`, does the same for one awaitable (also 0.50 s here). Since 3.11 both raise the built-in `TimeoutError`.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def lookup():\n    await asyncio.sleep(1)\n    return \"fresh\"\n\nasync def main():\n    try:\n        async with asyncio.timeout(0.05):\n            value = await lookup()\n    except TimeoutError:\n        value = \"stale\"\n    print(value)\n\nasyncio.run(main())",
  "answer": "stale",
  "explanation": "lookup needs 1 s, the deadline is 0.05 s. The timeout cancels it, converts the cancellation into TimeoutError at the async with, and the except outside the block uses the fallback." }
```

```quiz
{ "id": "q2", "type": "output", "label": "Debugging",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def main():\n    try:\n        async with asyncio.timeout(0.05):\n            try:\n                await asyncio.sleep(1)\n            except TimeoutError:\n                print(\"inner\")\n    except TimeoutError:\n        print(\"outer\")\n\nasyncio.run(main())",
  "answer": "outer",
  "explanation": "Inside the block, the sleep is interrupted by a CancelledError, which `except TimeoutError` doesn't match. The timeout context manager turns it into TimeoutError only when it leaves the async with." }
```

## 2. Cancellation is an exception at the `await`

`task.cancel()` **requests** cancellation. The docs: `CancelledError` is raised in the task at the next opportunity, which means at the `await` where it's suspended (or the next one it reaches). Timeouts, TaskGroups cancelling siblings and frameworks abandoning a request all use this same mechanism.

So cleanup goes in `finally`, exactly as for any exception:

```python
import asyncio

class Conn:
    open_count = 0
    def __init__(self):  Conn.open_count += 1
    def close(self):     Conn.open_count -= 1

async def upload(chunks):
    conn = Conn()
    try:
        for i in range(chunks):
            await asyncio.sleep(0.1)
            print("  sent chunk", i)
    finally:
        conn.close()            # runs on success, error AND cancellation
        print("  connection closed")

async def main():
    task = asyncio.create_task(upload(10))
    await asyncio.sleep(0.25)
    task.cancel()               # request cancellation
    try:
        await task
    except asyncio.CancelledError:
        print("upload cancelled; open connections:", Conn.open_count)
    print("task.cancelled():", task.cancelled())

asyncio.run(main())
```

```console
  sent chunk 0
  sent chunk 1
  connection closed
upload cancelled; open connections: 0
task.cancelled(): True
```

The cancellation hit the third `await asyncio.sleep(0.1)`, `finally` closed the connection, and the `CancelledError` kept going up, so the task ended up `cancelled()`. `async with` resources (locks, sessions, semaphores) release themselves the same way.

**Go comparison:** in Go, cancellation is a value you have to check (`select { case <-ctx.Done(): ... }`), and code that never checks keeps running. In asyncio it is *delivered* at the next `await` without you checking anything. The flip side: a long stretch with no `await` (AS.M01.L02) can't be cancelled either.

```quiz
{ "id": "q3", "type": "output", "label": "Predict the order",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def job():\n    try:\n        print(\"working\")\n        await asyncio.sleep(1)\n        print(\"done\")\n    finally:\n        print(\"cleanup\")\n\nasync def main():\n    t = asyncio.create_task(job())\n    await asyncio.sleep(0.05)\n    t.cancel()\n    try:\n        await t\n    except asyncio.CancelledError:\n        print(\"cancelled\")\n\nasyncio.run(main())",
  "answer": "working\ncleanup\ncancelled",
  "explanation": "CancelledError is raised at the sleep, so 'done' never prints; finally runs, then the error propagates out of the task and the await in main re-raises it." }
```

## 3. Never swallow `CancelledError`

`CancelledError` inherits from `BaseException`, not `Exception`, so `except Exception:` doesn't catch it. That's deliberate. But catching it explicitly and *not* re-raising breaks everything built on cancellation:

```python
import asyncio

async def stubborn():
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("  swallowed the cancellation")   # BUG: no raise
    return "finished anyway"

async def main():
    task = asyncio.create_task(stubborn())
    await asyncio.sleep(0.1)
    task.cancel()
    print(await task, "| cancelled:", task.cancelled())

    try:
        async with asyncio.timeout(0.1):
            result = await stubborn()
        print("timeout ignored:", result)
    except TimeoutError:
        print("timed out")

asyncio.run(main())
```

```console
  swallowed the cancellation
finished anyway | cancelled: False
  swallowed the cancellation
timeout ignored: finished anyway
```

The canceller was told "finished" and the **timeout silently didn't fire**: no `TimeoutError`, and the caller used a result it believes arrived in time. The same thing breaks TaskGroups, which rely on their cancelled tasks actually ending.

The docs' rule: use `try/finally` for cleanup; if you do catch `CancelledError` (to log, say), propagate it when cleanup is done. Suppressing cancellation is "actively discouraged" (and would also require `Task.uncancel()`). The right shape:

```python
except asyncio.CancelledError:
    log.info("upload cancelled")
    raise
```

Related tool: `asyncio.shield(aw)` protects an inner awaitable from cancellation (for a write that must complete), while the caller still gets `CancelledError`. Use it rarely and deliberately.

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "Catching `asyncio.CancelledError` to log a message and then returning a normal value is a safe way to handle cancellation.", "answer": false,
  "explanation": "The cancellation is lost: the caller thinks the work completed, asyncio.timeout won't raise TimeoutError, and a TaskGroup can't stop the task. Log, then re-raise." }
```

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "`async def handle(): lock_row(); await process(); unlock_row()`. Under load, rows stay locked forever after clients disconnect mid-request. What's the fix?",
  "options": ["Catch CancelledError after process() and return None", "Put unlock_row() in a finally block around await process()", "Wrap process() in asyncio.shield", "Use except Exception: unlock_row()"], "answer": 1,
  "explanation": "A disconnect cancels the task at `await process()`, skipping unlock_row. finally runs on cancellation too. except Exception wouldn't catch CancelledError (a BaseException), and swallowing it is wrong anyway." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Your async service calls a pricing API that sometimes hangs. Describe how you'd add a 300 ms deadline with a cached fallback, and what must be true of the code inside for the deadline to work.",
  "model": "Wrap the call in `async with asyncio.timeout(0.3):` inside a try, catch TimeoutError outside the block, and return the cached price there. For the deadline to work, the code inside must be awaiting (so cancellation can be delivered) and must not swallow CancelledError; any connection or lock it holds should be released in finally or async with.",
  "explanation": "Timeouts are cancellations; they only work if cancellation is allowed to propagate." }
```

## 4. Your turn

The exercise is a **debug** task: a query helper that leaks pooled connections on errors and cancellations, plus a "timeout" wrapper that has no timeout and swallows cancellation. The tests cancel a task from outside and check the pool afterwards.

```exercise
AS.M02.L03.E1
```
