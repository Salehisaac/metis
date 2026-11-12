---
{
  "id": "AS.M02.L02",
  "title": "When tasks fail: gather vs TaskGroup error semantics",
  "difficulty": "intermediate",
  "minutes": 90,
  "prerequisites": ["AS.M02.L01"],
  "objectives": [
    "Predict what happens to the other awaitables when one fails under gather, gather(return_exceptions=True) and TaskGroup",
    "Collect partial results with gather(..., return_exceptions=True) and separate failures from successes",
    "Catch errors from a TaskGroup with except* and explain why a plain except doesn't match",
    "Choose partial-results or all-or-nothing semantics for a given use case"
  ],
  "why": "With one call, an error is just an exception. With ten concurrent calls you must decide what happens to the other nine: keep running, get cancelled, or be reported. Getting it wrong leaves orphan work running after a request has failed, or throws away nine good results because of one bad one.",
  "applications": [
    "Health checks and dashboards that show partial results",
    "Building a response from required parts: fail fast and stop the rest",
    "Reading ExceptionGroup tracebacks from TaskGroups in logs"
  ],
  "exercises": ["AS.M02.L02.E1"],
  "sources": [
    {
      "title": "asyncio: Coroutines and Tasks (gather, TaskGroup)",
      "url": "https://docs.python.org/3.12/library/asyncio-task.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["gather with return_exceptions=False propagates the first exception immediately; other awaitables won't be cancelled and continue to run", "With return_exceptions=True exceptions are aggregated in the result list like results", "If gather() itself is cancelled, all unfinished awaitables are cancelled", "TaskGroup: on the first failure other than CancelledError the remaining tasks are cancelled; failures are combined in an ExceptionGroup", "If the body of the TaskGroup's async with raises, it's treated like a task failure"]
    },
    {
      "title": "Python Tutorial: Errors and Exceptions (ExceptionGroup, except*)",
      "url": "https://docs.python.org/3.12/tutorial/errors.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["ExceptionGroup wraps a list of exception instances so they can be raised together", "except* selectively handles the exceptions in the group that match a type; the rest propagate"]
    },
    {
      "title": "Package errgroup (golang.org/x/sync/errgroup)",
      "url": "https://pkg.go.dev/golang.org/x/sync/errgroup",
      "version": "golang.org/x/sync (current docs)",
      "verified": "2026-11-12",
      "claims": ["Wait returns the first non-nil error", "WithContext's Context is canceled the first time a function passed to Go returns a non-nil error"]
    }
  ]
}
---
## 1. Same failure, two outcomes

A product page needs `prices` and `reviews`. The prices service fails after 0.1 s; reviews would take 0.3 s. Watch what happens to `reviews`:

```python
import asyncio

async def service(name, secs, fail=False):
    try:
        await asyncio.sleep(secs)
        if fail:
            raise ConnectionError(f"{name} is down")
        print(f"  {name} finished")
        return name
    except asyncio.CancelledError:
        print(f"  {name} cancelled")
        raise

async def page_with_gather():
    try:
        await asyncio.gather(service("prices", 0.1, fail=True), service("reviews", 0.3))
    except ConnectionError as e:
        print("gather raised:", repr(e))
    await asyncio.sleep(0.4)   # keep the loop alive to see what happens to reviews

async def page_with_taskgroup():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(service("prices", 0.1, fail=True))
            tg.create_task(service("reviews", 0.3))
    except* ConnectionError as eg:
        print("TaskGroup raised:", repr(eg))
    await asyncio.sleep(0.4)

print("gather:")
asyncio.run(page_with_gather())
print("TaskGroup:")
asyncio.run(page_with_taskgroup())
```

```console
gather:
gather raised: ConnectionError('prices is down')
  reviews finished
TaskGroup:
  reviews cancelled
TaskGroup raised: ExceptionGroup('unhandled errors in a TaskGroup', [ConnectionError('prices is down')])
```

- **gather** raised the first error right away, and `reviews` **kept running** in the background and finished after the caller had already given up. The docs: the first exception is propagated immediately; the other awaitables won't be cancelled and will continue to run. In a server that's orphan work: wasted calls, and maybe side effects for a request that has already failed.
- **TaskGroup** cancelled `reviews`, **waited for it to finish cancelling**, and only then raised. The error arrives wrapped in an `ExceptionGroup`.

```quiz
{ "id": "q1", "type": "output", "label": "Predict the order",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def ok():\n    await asyncio.sleep(0.3)\n    print(\"ok finished\")\n    return 1\n\nasync def bad():\n    await asyncio.sleep(0.01)\n    raise ValueError(\"bad input\")\n\nasync def main():\n    try:\n        await asyncio.gather(ok(), bad())\n    except ValueError as e:\n        print(\"caught\", e)\n    await asyncio.sleep(0.4)\n\nasyncio.run(main())",
  "answer": "caught bad input\nok finished",
  "explanation": "gather propagates bad's error as soon as it happens, but doesn't cancel ok, which finishes later while main sleeps." }
```

## 2. Partial results: `return_exceptions=True`

Sometimes you want every outcome, good or bad: a health check, a dashboard with one broken widget. `gather(..., return_exceptions=True)` puts exceptions **into the result list** at their position, instead of raising:

```python
import asyncio

async def probe(host):
    await asyncio.sleep(0.01)
    if host == "db":
        raise TimeoutError("db timed out")
    return f"{host} ok"

async def main():
    results = await asyncio.gather(probe("api"), probe("db"), probe("cache"), return_exceptions=True)
    for r in results:
        print(type(r).__name__, r)

asyncio.run(main())
```

```console
str api ok
TimeoutError db timed out
str cache ok
```

Every probe ran to the end, and you check each result's type yourself. Don't forget that check: code that treats every item as a success will happily put an exception object into a JSON response.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def parse(text):\n    await asyncio.sleep(0)\n    return int(text)\n\nasync def main():\n    results = await asyncio.gather(parse(\"7\"), parse(\"x\"), return_exceptions=True)\n    print([type(r).__name__ for r in results])\n\nasyncio.run(main())",
  "answer": "['int', 'ValueError']",
  "explanation": "With return_exceptions=True the ValueError from int('x') becomes the second element of the result list instead of being raised." }
```

## 3. All-or-nothing: TaskGroup and `except*`

When the parts are useless without each other, use a TaskGroup: on the first failure it cancels the rest and raises an **`ExceptionGroup`** with every non-cancellation error. Because it's a group, a plain `except ValueError:` does **not** match it:

```quiz
{ "id": "q3", "type": "output", "label": "Debugging",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def boom():\n    raise ValueError(\"bad\")\n\nasync def main():\n    try:\n        async with asyncio.TaskGroup() as tg:\n            tg.create_task(boom())\n    except ValueError:\n        print(\"ValueError\")\n    except ExceptionGroup as eg:\n        print(\"group of\", len(eg.exceptions))\n\nasyncio.run(main())",
  "answer": "group of 1",
  "explanation": "The TaskGroup raises ExceptionGroup([ValueError('bad')]). An ExceptionGroup is not a ValueError, so the first clause doesn't match." }
```

Use **`except*`** to handle the matching exceptions inside a group. Each `except*` clause takes the part of the group that matches its type; the rest keeps propagating:

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import asyncio\n\nasync def fail(exc):\n    raise exc\n\nasync def main():\n    try:\n        async with asyncio.TaskGroup() as tg:\n            tg.create_task(fail(KeyError(\"a\")))\n            tg.create_task(fail(ValueError(\"b\")))\n    except* KeyError as eg:\n        print(\"keys:\", len(eg.exceptions))\n    except* ValueError as eg:\n        print(\"values:\", len(eg.exceptions))\n\nasyncio.run(main())",
  "answer": "keys: 1\nvalues: 1",
  "explanation": "Both tasks failed before either could be cancelled, so the group holds two exceptions. Unlike plain except, several except* clauses can run: each handles its own part of the group." }
```

Two `except*` rules that surprise people:

- `return`, `break` and `continue` aren't allowed inside an `except*` block (it's a `SyntaxError`). Set a variable and return after the `try`.
- `except*` also catches a *bare* exception: tried on this machine, `raise KeyError("k")` caught by `except* KeyError as eg` gives `eg = ExceptionGroup(..., (KeyError('k'),))`. So it works whether the code inside raises a group or not.

**Go comparison:** `errgroup.WithContext` gives you the same all-or-nothing shape: the context is cancelled on the first error, and `Wait` returns the **first** error. A TaskGroup reports **all** of the errors in the group, not just the first.

## 4. Choosing

| You want | Use |
|---|---|
| Every result; failures reported next to successes | `gather(..., return_exceptions=True)` |
| All parts or nothing; stop the rest on the first failure | `TaskGroup` (+ `except*`) |
| Plain `gather()` | Rarely: the first error escapes while the others keep running unobserved |

```quiz
{ "id": "q5", "type": "choice", "label": "Application",
  "prompt": "A checkout must reserve stock, authorize payment and compute shipping, concurrently. If any step fails the order is rejected. Which fits best?",
  "options": ["asyncio.gather() with defaults", "asyncio.gather(..., return_exceptions=True)", "asyncio.TaskGroup", "Three bare create_task calls without awaiting them"], "answer": 2,
  "explanation": "All-or-nothing: a TaskGroup cancels the other steps on the first failure and waits for them, so nothing keeps running for a rejected order. (Real checkouts also need compensation for steps that already completed.)" }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "A colleague uses plain asyncio.gather() to call 5 downstream services. When one fails, the endpoint returns 500, yet the logs show the other services still being called for a while. Explain why, and what you'd change.",
  "model": "gather propagates the first error immediately but does not cancel the other awaitables; they keep running after the endpoint has already failed. If the response needs all five, use a TaskGroup: it cancels the others and waits for them before raising. If partial results are fine, use gather(return_exceptions=True) and handle each failure.",
  "explanation": "Plain gather leaves orphan work behind." }
```

## 5. Your turn

The exercise has two functions that both use plain `gather`. One needs partial results, the other needs all-or-nothing. The tests check which tasks were cancelled, and when.

```exercise
AS.M02.L02.E1
```
