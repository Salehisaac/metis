```python
async def health_report(hosts, probe):
    up, down = {}, {}
    results = await asyncio.gather(*(probe(h) for h in hosts), return_exceptions=True)
    for host, result in zip(hosts, results):
        if isinstance(result, Exception):
            down[host] = result
        else:
            up[host] = result
    return up, down


async def load_settings(names, fetch):
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(n)) for n in names]
    return {name: task.result() for name, task in zip(names, tasks)}
```

**Why it works**

- **`return_exceptions=True`** makes gather treat an exception like a result: it lands in the result list at that probe's position and nothing propagates. Every probe runs to the end, and `zip` pairs hosts with outcomes by position.
- **The `isinstance(result, Exception)` check** separates failures from successes. (A cancelled probe would show up as a `CancelledError`, which is a `BaseException` but not an `Exception`; in this design nobody cancels individual probes, so that case doesn't arise.)
- **The TaskGroup** gives all-or-nothing semantics: when one fetch raises, the group cancels the others, *waits for them to finish cancelling*, and only then raises an `ExceptionGroup` with the failure. That's why the test sees both "cancelled" entries at the moment the error arrives.

**Which to use when**

- Report, dashboard, fan-out where partial results are useful: `gather(..., return_exceptions=True)`.
- A unit of work that is useless if any part fails (loading required config, building one response from required parts): `TaskGroup`. It is the asyncio counterpart of Go's `errgroup.WithContext`, whose context is cancelled when the first function returns an error.

**Common mistake:** catching `KeyError` with a plain `except KeyError:` around a TaskGroup. The error arrives wrapped in an `ExceptionGroup`, so a plain `except KeyError` doesn't match; use `except* KeyError`.
