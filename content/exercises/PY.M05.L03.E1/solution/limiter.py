import time
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Anything with a now() method returning seconds as a float."""

    def now(self) -> float: ...


class SystemClock:
    """The real clock (monotonic: never jumps backwards)."""

    def now(self) -> float:
        return time.monotonic()


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
    """Allow at most `limit` calls in any `window` seconds.

    A call allowed at time t counts against the limit until t + window (exclusive).
    """

    def __init__(self, limit: int, window: float, clock: Clock | None = None) -> None:
        self.clock = clock if clock is not None else SystemClock()
        self.limit = limit
        self.window = window
        self._allowed_at: list[float] = []

    def allow(self) -> bool:
        now = self.clock.now()
        self._allowed_at = [t for t in self._allowed_at if now - t < self.window]
        if len(self._allowed_at) >= self.limit:
            return False
        self._allowed_at.append(now)
        return True
