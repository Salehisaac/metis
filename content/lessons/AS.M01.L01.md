---
{
  "id": "AS.M01.L01",
  "title": "Coroutines and await: what really happens (no threads)",
  "difficulty": "intermediate",
  "minutes": 90,
  "prerequisites": ["PY.M07"],
  "objectives": [
    "Explain that calling an async def function returns a coroutine object and runs none of its body",
    "Predict the print order of a program that awaits a coroutine, and of one that creates tasks",
    "State precisely what await does: it suspends the current coroutine until the awaited thing has a result, on the same thread, and starts no thread",
    "Spot a missing await from its symptoms (a coroutine object where a value was expected, the 'never awaited' RuntimeWarning) and fix it"
  ],
  "why": "Your assessment answer was that `await` starts a thread. That model predicts the wrong output for almost every async program, and in FastAPI it leads to the classic mistakes: blocking the server and forgetting awaits. This lesson replaces it with the real model before anything else is built on it.",
  "applications": [
    "Reading and writing async FastAPI endpoints (AS.M03)",
    "Calling async clients: httpx.AsyncClient, async database drivers, async Redis",
    "Debugging 'coroutine was never awaited' warnings and 'coroutine object is not subscriptable' errors"
  ],
  "exercises": ["AS.M01.L01.E1"],
  "sources": [
    {
      "title": "asyncio: Coroutines and Tasks",
      "url": "https://docs.python.org/3.12/library/asyncio-task.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Simply calling a coroutine will not schedule it; a coroutine object is created but won't run", "asyncio.run() runs the top-level entry point", "Save a reference to the task from create_task; the event loop only keeps weak references", "sleep() always suspends the current task, allowing other tasks to run"]
    },
    {
      "title": "Developing with asyncio (concurrency and multithreading; never-awaited coroutines)",
      "url": "https://docs.python.org/3.12/library/asyncio-dev.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["An event loop runs in a thread (typically the main thread) and executes all callbacks and Tasks in its thread", "While a Task is running in the event loop, no other Tasks can run in the same thread", "A coroutine called but not awaited (or scheduled with create_task) emits RuntimeWarning: coroutine ... was never awaited"]
    },
    {
      "title": "A Conceptual Overview of asyncio (HOWTO)",
      "url": "https://docs.python.org/3.13/howto/a-conceptual-overview-of-asyncio.html",
      "version": "Python 3.13 docs (3.13.18); this page does not exist in the 3.12 docs; installed 3.12.3",
      "verified": "2026-11-12",
      "claims": ["Everything in asyncio happens relative to the event loop", "Awaiting a task cedes control from the current task to the event loop", "Unlike tasks, awaiting a coroutine does not hand control back to the event loop; it behaves like calling a regular function"]
    }
  ]
}
---
## 1. Calling an async function runs nothing

You know generators from PY.M07: calling a generator function runs none of its body, it hands you a generator object that something must drive. `async def` works the same way. Calling it returns a **coroutine object**, and the body doesn't start:

```python
import asyncio

async def price(item):
    print("pricing", item)
    return 10

c = price("tea")
print(type(c).__name__)
print(asyncio.run(c))
```

```console
coroutine
pricing tea
10
```

`pricing tea` appears only when `asyncio.run` drives the coroutine. The Python docs say it directly: simply calling a coroutine does not schedule it, and a coroutine object that is never awaited won't run at all.

Go has no equivalent: `f()` runs `f`, and `go f()` runs it concurrently. In Python, `price("tea")` is closer to *building* the call than *making* it.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "async def ping():\n    print(\"ran\")\n    return \"pong\"\n\nc = ping()\nprint(type(c).__name__)\nc.close()  # discard it without running (avoids a warning)",
  "answer": "coroutine",
  "explanation": "Calling ping() only creates a coroutine object; its body (the print) never runs. close() throws it away." }
```

## 2. `await` does not start a thread

Here is the key claim of this whole module. **`await x` means: suspend the coroutine I'm in until `x` has a result, then continue with that result.** Nothing runs "in the background", and no thread is created. `asyncio.run` starts **one event loop on the current thread**, and every coroutine and task in it runs on that thread. The asyncio docs: an event loop runs in a thread and executes all callbacks and Tasks in its thread.

Predict the order before you read the answer:

```quiz
{ "id": "q2", "type": "output", "label": "Predict the order",
  "prompt": "What does this print? Write the lines in order.",
  "code": "import asyncio\n\nasync def child():\n    print(\"child start\")\n    await asyncio.sleep(0.1)\n    print(\"child end\")\n\nasync def main():\n    print(\"main before\")\n    await child()\n    print(\"main after\")\n\nasyncio.run(main())",
  "answer": "main before\nchild start\nchild end\nmain after",
  "explanation": "await child() runs child right now, and main waits at that line until child has returned. If await started a thread, you'd expect 'main after' before 'child end'. It can't be: main is suspended until child finishes." }
```

If you answered with `main after` before `child end`, that's the thread model talking. Drop it: **`await` is a function call that can pause.** The official asyncio HOWTO puts it even more bluntly: awaiting a coroutine does not hand control back to the event loop; it behaves like calling a regular function. Control only goes back to the loop when something further down really has to wait, here `asyncio.sleep`.

Proof that no thread appears, run on this machine:

```python
import asyncio, threading

async def step(name):
    print(name, "thread", threading.get_ident() == MAIN)
    await asyncio.sleep(0.1)
    print(name, "resumed, thread", threading.get_ident() == MAIN)

async def main():
    print("threads before:", threading.active_count())
    await step("a")
    print("threads after:", threading.active_count())

MAIN = threading.get_ident()
asyncio.run(main())
```

```console
threads before: 1
a thread True
a resumed, thread True
threads after: 1
```

One thread before, one thread after, and the code before and after the `await` ran on the main thread both times.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import asyncio, threading\n\nasync def work():\n    await asyncio.sleep(0.05)\n    return threading.current_thread().name\n\nasync def main():\n    name = await work()\n    print(name, threading.active_count())\n\nasyncio.run(main())",
  "answer": "MainThread 1",
  "explanation": "The coroutine ran, slept and resumed on the main thread, and there is still exactly one thread. await created none." }
```

## 3. Sequential awaits are sequential

So where does async concurrency come from? Not from `await` itself. Two awaits in a row are two calls in a row:

```python
import asyncio, time

async def call(name, secs):
    print("start", name)
    await asyncio.sleep(secs)
    print("end", name)

async def main():
    t = time.perf_counter()
    await call("a", 1)
    await call("b", 1)
    print(f"took {time.perf_counter() - t:.2f}s")

asyncio.run(main())
```

```console
start a
end a
start b
end b
took 2.00s
```

2 seconds, exactly like synchronous code. Concurrency appears when you hand coroutines to the event loop as **tasks**. `asyncio.create_task(coro)` wraps the coroutine in a task and schedules it; the loop starts running it as soon as the current coroutine suspends. Same `call` as above:

```python
async def main():
    t = time.perf_counter()
    ta = asyncio.create_task(call("a", 1))
    tb = asyncio.create_task(call("b", 1))
    await ta
    await tb
    print(f"took {time.perf_counter() - t:.2f}s")
```

```console
start a
start b
end a
end b
took 1.00s
```

Measured on this machine: 1.00 s. While `a` sleeps, the loop runs `b`. Both waits overlap, and still **on one thread**. That's the asyncio deal: concurrency while *waiting*, not parallel execution. A task is the nearest thing to `go f()`, with one big difference that L02 is about.

Keep the task objects in variables (as above). The docs warn that the event loop only keeps weak references to tasks, so a task nobody references can disappear before it's done. AS.M02 covers tasks, `gather` and `TaskGroup` properly.

```quiz
{ "id": "q4", "type": "choice", "label": "Predict the order",
  "prompt": "`main` runs `t1 = asyncio.create_task(job(1))`, then `t2 = asyncio.create_task(job(2))`, then `print(\"tasks created\")`, then `await t1`. Each job prints \"start N\" as its first line. Which line is printed first?",
  "options": ["start 1", "tasks created", "start 2", "It varies from run to run"], "answer": 1,
  "explanation": "create_task only schedules the task. It can't start until main suspends, and main doesn't suspend until `await t1`. So main's print comes first, always." }
```

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "While one task is suspended at `await asyncio.sleep(1)`, other tasks on the same event loop can run.", "answer": true,
  "explanation": "The docs: sleep() always suspends the current task, allowing other tasks to run. Only the suspended task waits; the loop keeps working." }
```

## 4. The missing `await`

Because calling a coroutine function is legal and returns an object, forgetting `await` is not a syntax error. You get a coroutine where you expected a value, and the error shows up somewhere else:

```python
import asyncio

async def load_profile(user_id):
    await asyncio.sleep(0)
    return {"id": user_id, "name": "Sara"}

async def main():
    profile = load_profile(7)      # forgot await
    print(profile["name"])

asyncio.run(main())
```

```console
Traceback (most recent call last):
  ...
    print(profile["name"])
          ~~~~~~~^^^^^^^^
TypeError: 'coroutine' object is not subscriptable
sys:1: RuntimeWarning: coroutine 'load_profile' was never awaited
```

Two clues to remember:

- **Errors that mention `'coroutine' object`.** A coroutine was used as if it were its result.
- **`RuntimeWarning: coroutine '...' was never awaited`.** The asyncio docs list exactly this warning; the fix is to await the coroutine (or schedule it with `create_task`). pytest shows these warnings in its summary, so read them.

Worse than a crash: a coroutine object is **truthy**, so `if some_async_check():` silently takes the `True` branch. A missing await can return wrong data without any exception at all.

Two other rules you'll hit:

- `await` is only allowed inside `async def`. Using it in a normal `def` is a `SyntaxError`.
- `asyncio.run()` is for the program's entry point. Inside a coroutine, you `await`; you don't call `asyncio.run` again.

```quiz
{ "id": "q6", "type": "choice", "label": "Debugging",
  "prompt": "`rows = db.fetch_all(\"SELECT ...\")` followed by `for r in rows:` raises `TypeError: 'coroutine' object is not iterable`. What's wrong?",
  "options": ["fetch_all is async and its call wasn't awaited", "The query returned no rows", "The loop must be `async for`", "fetch_all ran in a different thread"], "answer": 0,
  "explanation": "'coroutine' object in an error message means a coroutine was used as if it were its result. Write rows = await db.fetch_all(...)." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "A teammate says: \"`await` runs the call in a background thread so the server can keep going.\" Correct them in two or three sentences.",
  "model": "await doesn't create a thread. It suspends the current coroutine until the awaited thing has a result; all coroutines and tasks run on the event loop's one thread. The server keeps going because, while this coroutine is suspended waiting for I/O, the event loop runs other tasks on that same thread.",
  "explanation": "Concurrency comes from the loop switching between suspended tasks, not from threads." }
```

## 5. Your turn

The exercise is a **debug** task: a cart service that calls async functions but forgot some awaits. One of the bugs crashes; another one silently charges for an item that's out of stock. Read pytest's warnings: they point at the lines.

```exercise
AS.M01.L01.E1
```
