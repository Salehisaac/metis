import asyncio
import threading
import time


def run(coro):
    async def bounded():
        async with asyncio.timeout(5):
            return await coro
    return asyncio.run(bounded())


class FakeGeocoder:
    """A blocking geocoder: each call sleeps (blocks its thread) and records where it ran."""

    def __init__(self, delay=0.15):
        self.delay = delay
        self.calls = []
        self.threads = set()

    def __call__(self, city):
        self.calls.append(city)
        self.threads.add(threading.get_ident())
        time.sleep(self.delay)
        if city == "Atlantis":
            raise LookupError(city)
        return (float(len(city)), 1.0)


async def _with_heartbeat(coro):
    ticks = []
    stop = False

    async def beat():
        while not stop:
            ticks.append(1)
            await asyncio.sleep(0.01)

    hb = asyncio.create_task(beat())
    await asyncio.sleep(0)
    try:
        result = await coro
    finally:
        stop = True
        await hb
    return result, len(ticks)


def test_results():
    import geo
    g = FakeGeocoder(delay=0)
    assert run(geo.locate_all(["Tehran", "Oslo"], g)) == {"Tehran": (6.0, 1.0), "Oslo": (4.0, 1.0)}


def test_geocode_runs_off_the_loop_thread():
    import geo
    g = FakeGeocoder(delay=0)
    run(geo.locate_all(["Oslo"], g))
    assert threading.get_ident() not in g.threads, "geocode ran on the event loop's thread"


def test_loop_stays_responsive():
    import geo
    g = FakeGeocoder(delay=0.15)
    _, ticks = run(_with_heartbeat(geo.locate_all(["Tehran", "Oslo"], g)))
    # 0.3 s of blocking calls; a free loop ticks about every 0.01 s. A blocked one ticks once.
    assert ticks >= 5, f"heartbeat ticked only {ticks} time(s): the loop was blocked"


def test_duplicates_geocoded_once():
    import geo
    g = FakeGeocoder(delay=0)
    out = run(geo.locate_all(["Oslo", "Oslo", "Rome", "Oslo"], g))
    assert sorted(g.calls) == ["Oslo", "Rome"]
    assert list(out) == ["Oslo", "Rome"]


def test_empty_list_makes_no_calls():
    import geo
    g = FakeGeocoder(delay=0)
    assert run(geo.locate_all([], g)) == {}
    assert g.calls == []


def test_errors_propagate():
    import geo
    g = FakeGeocoder(delay=0)
    try:
        run(geo.locate_all(["Oslo", "Atlantis"], g))
    except LookupError as e:
        assert str(e) == "Atlantis"
    else:
        raise AssertionError("LookupError from geocode should reach the caller")
