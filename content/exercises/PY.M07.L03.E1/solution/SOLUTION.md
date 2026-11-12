```python
import functools


def retry(times, exceptions=(Exception,)):
    if times < 1:
        raise ValueError(f"times must be at least 1, got {times}")

    def decorate(func):
        @functools.wraps(func)
        def call_with_retry(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == times:
                        raise

        return call_with_retry

    return decorate
```

**Why it works**

- **Three layers.** `retry(3)` runs once, when the `@retry(3)` line is executed, and returns `decorate`. Python then calls `decorate(fetch)` and binds the returned `call_with_retry` to the name `fetch`. `call_with_retry` runs on every call. The `ValueError` check is in the outer layer, so a bad `times` fails at definition time, not on the first request in production.
- **`return` inside `try` ends the loop.** The first successful call returns its result straight out of the wrapper.
- **`except exceptions:`** takes a tuple of types and matches instances of their subclasses, so `exceptions=(OSError,)` also retries `ConnectionError`. Everything else isn't caught, so it propagates on the first attempt.
- **Bare `raise`** re-raises the exception currently being handled, unchanged, with its original traceback. On the earlier attempts the `except` block ends without raising, so the loop goes on to the next attempt.
- **Fresh attempts per call.** `attempt` is a local variable of `call_with_retry`, created anew on every call. If you kept a counter in `decorate`'s scope (with `nonlocal`), it would be shared by all calls, and the second call would start with no attempts left. `test_each_call_gets_fresh_attempts` checks this.
- **`functools.wraps(func)`** copies `__name__`, `__doc__` and the other metadata, and sets `__wrapped__`. Without it, every decorated function would be called `call_with_retry` in tracebacks and logs.

**Alternatives and real-world notes**

- Production retry adds a delay with exponential backoff and jitter (`time.sleep(base * 2 ** attempt)`), and retries only operations that are safe to repeat (idempotent), the same rule as for retries in Go services.
- A `while` loop with a counter works too, but the `for attempt in range(...)` version can't loop forever by mistake.
