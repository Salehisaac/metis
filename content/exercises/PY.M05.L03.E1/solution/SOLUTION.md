The changed parts of `limiter.py`:

```python
class FakeClock:
    """Test clock: starts at `start` and moves only when advance() is called."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError(f"a clock can't go backwards: {seconds}")
        self._now += seconds


class SlidingWindowLimiter:
    def __init__(self, limit: int, window: float, clock: Clock | None = None) -> None:
        self.clock = clock if clock is not None else SystemClock()
        self.limit = limit
        self.window = window
        self._allowed_at: list[float] = []

    def allow(self) -> bool:
        now = self.clock.now()
        ...  # unchanged
```

**Why it works**

- **Structural typing.** `FakeClock` has a `now() -> float` method, and that's all `Clock` asks for. Exactly like a Go type satisfying an interface implicitly, it never names `Clock`. `isinstance(FakeClock(), Clock)` is `True` only because the starter marked `Clock` `@runtime_checkable`, and that check looks only for a `now` attribute, not its signature.
- **Dependency injection.** The limiter no longer decides where time comes from; the caller does. Production code calls `SlidingWindowLimiter(5, 60.0)` and gets the real clock. Tests pass a `FakeClock` and move time instantly, so "wait out the window" takes microseconds and gives the same result every run. This is the same reason Go code takes a `Clock` interface or a `now func() time.Time`.
- **`clock=None`, not `clock=SystemClock()`.** A default is evaluated once, when `def` runs (PY.M02.L04), so every limiter would share one `SystemClock`. That's harmless here, because `SystemClock` has no state, but the `None` default keeps working when the default object does have state.
- **`if clock is not None`** rather than `clock or SystemClock()`: `or` would also replace any clock object that happens to be falsy (for example one that defines `__len__` and returns 0). `is not None` says exactly what you mean.
- **Errors before mutation:** `advance` checks first, so a rejected call leaves the time unchanged.
- **The window boundary** comes from the unchanged `now - t < self.window`: at exactly `t + window` the difference equals `window`, so the old call is dropped and a new call is allowed.

**Alternative:** inject a function instead of an object, `now: Callable[[], float] = time.monotonic`, and call `self.now()`. With a single method that's lighter. A protocol is nicer when the dependency has several methods or keeps state, like `FakeClock.advance`.
