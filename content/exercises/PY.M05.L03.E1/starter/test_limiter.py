import pytest


def test_fake_clock_starts_at_given_time():
    from limiter import FakeClock
    assert FakeClock().now() == 0.0
    assert FakeClock(100.0).now() == 100.0


def test_fake_clock_advance():
    from limiter import FakeClock
    clock = FakeClock(10.0)
    clock.advance(2.5)
    clock.advance(0)
    assert clock.now() == 12.5
    assert clock.now() == 12.5


def test_fake_clock_rejects_going_backwards():
    from limiter import FakeClock
    clock = FakeClock(5.0)
    with pytest.raises(ValueError):
        clock.advance(-1)
    assert clock.now() == 5.0


def test_fake_clock_satisfies_protocol_without_inheriting():
    from limiter import Clock, FakeClock
    assert isinstance(FakeClock(), Clock)
    assert Clock not in FakeClock.__mro__


def test_limiter_blocks_after_limit():
    from limiter import FakeClock, SlidingWindowLimiter
    clock = FakeClock()
    limiter = SlidingWindowLimiter(2, 10.0, clock=clock)
    assert limiter.allow() is True
    clock.advance(1)
    assert limiter.allow() is True
    assert limiter.allow() is False
    clock.advance(8.9)
    assert limiter.allow() is False


def test_limiter_frees_slot_exactly_at_window():
    from limiter import FakeClock, SlidingWindowLimiter
    clock = FakeClock()
    limiter = SlidingWindowLimiter(1, 10.0, clock=clock)
    assert limiter.allow() is True
    clock.advance(9.5)
    assert limiter.allow() is False
    clock.advance(0.5)
    assert limiter.allow() is True
    assert limiter.allow() is False


def test_limiters_are_independent():
    from limiter import FakeClock, SlidingWindowLimiter
    clock = FakeClock()
    a = SlidingWindowLimiter(1, 10.0, clock=clock)
    b = SlidingWindowLimiter(1, 10.0, clock=clock)
    assert a.allow() is True
    assert b.allow() is True


def test_limiter_uses_real_clock_by_default():
    from limiter import SlidingWindowLimiter, SystemClock
    limiter = SlidingWindowLimiter(1, 60.0)
    assert isinstance(limiter.clock, SystemClock)
    assert limiter.allow() is True
    assert limiter.allow() is False
