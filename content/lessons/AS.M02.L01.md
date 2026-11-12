---
{
  "id": "AS.M02.L01",
  "title": "Tasks, gather and TaskGroup: running I/O concurrently",
  "difficulty": "intermediate",
  "minutes": 90,
  "prerequisites": ["AS.M01"],
  "objectives": [
    "Turn sequential awaits into concurrent ones with asyncio.gather and asyncio.TaskGroup, and measure the difference",
    "State the result order of gather and how to read results from TaskGroup tasks",
    "Explain why a bare create_task needs a stored reference, and why TaskGroup is the safer default",
    "Recognise the 'create a task and await it immediately' pattern as sequential"
  ],
  "why": "Almost every backend endpoint fans out: user + orders + recommendations, or N items from a cache. Sequential awaits add the latencies up; concurrent ones cost about the slowest call. This is the main reason to use async at all.",
  "applications": [
    "Building one API response from several independent service calls",
    "Fetching many keys or URLs at once",
    "Replacing Go's WaitGroup / errgroup fan-out patterns in Python"
  ],
  "exercises": ["AS.M02.L01.E1"],
  "sources": [
    {
      "title": "asyncio: Coroutines and Tasks (create_task, gather, TaskGroup)",
      "url": "https://docs.python.org/3.12/library/asyncio-task.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["gather schedules coroutines as Tasks automatically; the order of result values corresponds to the order of awaitables", "TaskGroup was added in 3.11; async with waits for all tasks in the group to finish", "TaskGroup provides stronger safety guarantees than gather: on an exception it cancels the remaining scheduled tasks", "Save a reference to the result of create_task; the event loop only keeps weak references to tasks"]
    },
    {
      "title": "Package errgroup (golang.org/x/sync/errgroup)",
      "url": "https://pkg.go.dev/golang.org/x/sync/errgroup",
      "version": "golang.org/x/sync (current docs)",
      "verified": "2026-11-12",
      "claims": ["Wait blocks until all function calls from Go have returned, then returns the first non-nil error", "WithContext's derived Context is canceled the first time a function passed to Go returns a non-nil error"]
    }
  ]
}
---
## 1. The fan-out problem

From AS.M01: `await` waits, a task lets the loop run something else meanwhile, and everything happens on one thread. Now put that to work. An endpoint needs three independent service calls (simulated with `asyncio.sleep`). Three ways to make them, measured on this machine:

```python
import asyncio, time

async def get_json(service, secs):
    await asyncio.sleep(secs)          # stands in for an HTTP call
    return {"service": service}

async def sequential():
    user = await get_json("users", 0.3)
    orders = await get_json("orders", 0.5)
    recs = await get_json("recs", 0.2)
    return user, orders, recs

async def with_gather():
    return await asyncio.gather(
        get_json("users", 0.3), get_json("orders", 0.5), get_json("recs", 0.2)
    )

async def with_taskgroup():
    async with asyncio.TaskGroup() as tg:
        u = tg.create_task(get_json("users", 0.3))
        o = tg.create_task(get_json("orders", 0.5))
        r = tg.create_task(get_json("recs", 0.2))
    return u.result(), o.result(), r.result()

for fn in (sequential, with_gather, with_taskgroup):
    t = time.perf_counter()
    res = asyncio.run(fn())
    print(f"{fn.__name__:15} {time.perf_counter() - t:.2f}s {[d['service'] for d in res]}")
```

```console
sequential      1.00s ['users', 'orders', 'recs']
with_gather     0.50s ['users', 'orders', 'recs']
with_taskgroup  0.50s ['users', 'orders', 'recs']
```

Sequential costs the sum (0.3 + 0.5 + 0.2 = 1.0 s). Concurrent costs the slowest call (0.5 s). Both concurrent versions start all three calls before waiting for any of them.

## 2. `asyncio.gather`

`await asyncio.gather(a, b, c)` schedules each coroutine as a task, waits until all are done, and returns their results **in the order you passed them**, not the order they finished:

```quiz
{ "id": "q1", "type": "output", "label": "Predict the order",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def wait_then(name, secs):\n    await asyncio.sleep(secs)\n    print(\"finished\", name)\n    return name\n\nasync def main():\n    results = await asyncio.gather(wait_then(\"slow\", 0.2), wait_then(\"fast\", 0.1))\n    print(results)\n\nasyncio.run(main())",
  "answer": "finished fast\nfinished slow\n['slow', 'fast']",
  "explanation": "The tasks finish fast-first, but gather's result list follows the argument order: the docs say the order of result values corresponds to the order of awaitables." }
```

With a list of inputs, unpack a generator: `await asyncio.gather(*(fetch(u) for u in urls))`, then `zip(urls, results)` pairs them up.

## 3. `asyncio.TaskGroup` (Python 3.11+)

A `TaskGroup` is an `async with` block that owns tasks:

- `tg.create_task(coro)` starts a task in the group.
- **The block doesn't exit until every task in the group has finished.** After it, each task's `.result()` is ready.
- If a task fails, the group cancels the others (next lesson).

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def main():\n    async with asyncio.TaskGroup() as tg:\n        t = tg.create_task(asyncio.sleep(0.1, result=\"done\"))\n        print(\"inside:\", t.done())\n    print(\"after:\", t.done(), t.result())\n\nasyncio.run(main())",
  "answer": "inside: False\nafter: True done",
  "explanation": "Inside the block the task has only been scheduled. Leaving the block waits for every task, so afterwards it is done and .result() returns its value." }
```

**Go comparison.** A TaskGroup is `sync.WaitGroup` plus error handling and cancellation built in, which is close to `errgroup.WithContext`: `Wait()` blocks until all functions return, and the context is cancelled on the first error. In Go you have to pass `ctx` down and check it; in asyncio the group cancels the tasks for you (L02, L03).

`gather` or `TaskGroup`? For new code, prefer the TaskGroup: the docs say it gives stronger safety guarantees than gather, because when a task fails it cancels the remaining ones. `gather` is still useful, especially `gather(..., return_exceptions=True)` for partial results (L02).

## 4. Bare `create_task`, and a classic mistake

`asyncio.create_task(coro)` without a group also starts a task. Two things to know:

- **Keep a reference.** The docs warn that the event loop only keeps *weak* references to tasks, so a task that isn't referenced elsewhere may be garbage-collected before it's done. "Fire and forget" with an unreferenced `create_task(...)` can silently lose work. A TaskGroup holds its tasks for you.
- **Creating a task and awaiting it right away is sequential:**

```python
results = []
for s in services:
    results.append(await asyncio.create_task(call(s)))   # starts one, waits for it, then the next
```

Each iteration waits for its task before creating the next, so only one call is ever in flight. Create all the tasks first, *then* wait.

```quiz
{ "id": "q3", "type": "choice", "label": "Debugging",
  "prompt": "This loop is supposed to fetch 10 pages concurrently but takes 10 times as long as one fetch: `for u in urls: pages.append(await asyncio.create_task(fetch(u)))`. Why?",
  "options": ["create_task runs the coroutine in a thread pool that has one thread", "Each task is awaited before the next one is created, so they run one at a time", "Tasks only run concurrently with gather", "fetch must be a def function"], "answer": 1,
  "explanation": "The await inside the loop body waits for the task to finish before the loop continues. Create all tasks first (or use gather / a TaskGroup), then await." }
```

## 5. Tasks are cheap, but they share one thread

A task costs little memory and no thread, like a goroutine. Ten thousand concurrent sleeps, measured on this machine:

```python
import asyncio, time

async def main():
    t = time.perf_counter()
    await asyncio.gather(*(asyncio.sleep(1) for _ in range(10_000)))
    print(f"10000 sleeps: {time.perf_counter() - t:.2f}s")

asyncio.run(main())
```

```console
10000 sleeps: 1.03s
```

But remember AS.M01: they all share **one** thread. Ten thousand concurrent *waits* is fine. Ten thousand concurrent requests to one database is not: L04 is about limiting that.

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "`asyncio.gather` runs its coroutines in parallel on several CPU cores.", "answer": false,
  "explanation": "gather runs them concurrently on the event loop's single thread: their waits overlap, but only one runs Python code at any moment. CPU work doesn't get faster." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Application",
  "prompt": "An endpoint awaits get_user (80 ms), then get_orders (120 ms), then get_prefs (40 ms); none depends on another. Roughly how long does it take now, how long after your change, and what would you change?",
  "model": "Now about 240 ms (the sum). Start all three at once with a TaskGroup (or gather) and read the results afterwards: about 120 ms, the slowest call. This only works because the calls are independent; a call that needs another's result must still wait for it.",
  "explanation": "Sequential awaits add up; concurrent tasks cost the slowest one." }
```

## 6. Your turn

The exercise is a quote fetcher that awaits each lookup in turn. Make it concurrent, keep the input order, and don't fetch duplicates twice. The fake API in the tests counts how many lookups are in flight at the same time.

```exercise
AS.M02.L01.E1
```
