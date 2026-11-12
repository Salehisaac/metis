---
{ "id": "AS.M02.A", "module": "AS.M02", "title": "AS.M02 module assessment: tasks, gather, timeouts, cancellation", "minutes": 15 }
---
Answer without the lessons open and without AI, and don't run the code first. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before AS.M03.

```quiz
{ "id": "a1", "type": "output", "label": "Predict the order",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def step(name, secs):\n    await asyncio.sleep(secs)\n    print(name)\n    return name\n\nasync def main():\n    async with asyncio.TaskGroup() as tg:\n        a = tg.create_task(step(\"a\", 0.2))\n        b = tg.create_task(step(\"b\", 0.1))\n    print(a.result() + b.result())\n\nasyncio.run(main())",
  "answer": "b\na\nab",
  "explanation": "Both tasks run concurrently, so b (0.1 s) prints before a (0.2 s). The block exits once both are done, and the results are read by task, not by finish order." }
```

```quiz
{ "id": "a2", "type": "choice",
  "prompt": "`await asyncio.gather(charge_card(), send_receipt())` and `charge_card()` raises. What happens to `send_receipt()`?",
  "options": ["It is cancelled before gather raises", "It keeps running; gather raises the error immediately", "gather waits for it, then raises an ExceptionGroup", "It never started"], "answer": 1,
  "explanation": "With the default return_exceptions=False, gather propagates the first exception immediately and does not cancel the other awaitables. A TaskGroup would cancel it." }
```

```quiz
{ "id": "a3", "type": "output", "label": "Predict the order",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def save():\n    try:\n        await asyncio.sleep(1)\n        print(\"saved\")\n    except asyncio.CancelledError:\n        print(\"rollback\")\n        raise\n    finally:\n        print(\"close\")\n\nasync def main():\n    try:\n        async with asyncio.timeout(0.05):\n            await save()\n    except TimeoutError:\n        print(\"timeout\")\n\nasyncio.run(main())",
  "answer": "rollback\nclose\ntimeout",
  "explanation": "The deadline cancels the task: CancelledError arrives at the sleep, the handler prints and re-raises, finally runs, and the timeout context manager converts the cancellation into TimeoutError outside the block." }
```

```quiz
{ "id": "a4", "type": "truefalse",
  "prompt": "`except Exception:` around an await catches the `asyncio.CancelledError` raised when the task is cancelled.", "answer": false,
  "explanation": "Since Python 3.8 CancelledError subclasses BaseException, not Exception, so cancellation passes through `except Exception` unharmed, as intended." }
```

```quiz
{ "id": "a5", "type": "choice", "label": "Debugging",
  "prompt": "`async def fetch(url): async with asyncio.Semaphore(10): return await client.get(url)` is meant to keep at most 10 requests in flight across 1,000 concurrent calls. How many can actually be in flight?",
  "options": ["10", "1", "All 1,000", "It deadlocks"], "answer": 2,
  "explanation": "Every call creates its own semaphore with 10 permits, so no call ever waits. Create one semaphore and share it between all calls." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Design the concurrency for an endpoint that must call 3 required services (any failure means 502) with a 1-second overall deadline, plus an optional ads service whose failure must not affect the response. Name the asyncio tools and where cleanup goes.",
  "model": "Wrap everything in async with asyncio.timeout(1.0) and catch TimeoutError outside it (return 504/502). Run the 3 required calls in a TaskGroup so the first failure cancels the others; catch their errors with except* and return 502. Run ads separately, e.g. gather(ads(), return_exceptions=True) or a task whose exception is caught, and fall back to no ads. Resources (connections, locks) are released in finally / async with, and CancelledError is never swallowed so the deadline and the TaskGroup can stop work.",
  "explanation": "Timeout for the deadline, TaskGroup for all-or-nothing, return_exceptions or a caught task for optional work, finally for cleanup." }
```
