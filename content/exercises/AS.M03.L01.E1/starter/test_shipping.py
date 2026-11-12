import asyncio
import threading

import httpx


def run(coro):
    async def bounded():
        async with asyncio.timeout(5):
            return await coro
    return asyncio.run(bounded())


def install_barrier_carrier(shipping, parties=2):
    """Replace the SDK with a fake that only answers once `parties` calls are waiting at the same time.

    If the endpoint blocks the event loop, the second request can't start, the barrier
    times out after 1 s and the fake raises threading.BrokenBarrierError.
    """
    barrier = threading.Barrier(parties, timeout=1)
    loop_thread = threading.get_ident()
    seen_threads = []

    def fake(country):
        seen_threads.append(threading.get_ident())
        barrier.wait()
        return shipping.RATES.get(country)

    shipping.carrier_quote = fake
    return loop_thread, seen_threads


async def get_all(app, paths):
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await asyncio.gather(*(client.get(p) for p in paths))


def fresh():
    import importlib
    import shipping
    return importlib.reload(shipping)


def test_quote_values():
    shipping = fresh()
    shipping.carrier_quote = lambda c: shipping.RATES.get(c)
    r_de, r_us = run(get_all(shipping.app, ["/quote/DE", "/quote/US/USD"]))
    assert r_de.status_code == 200 and r_de.json() == {"country": "DE", "eur": 12}
    assert r_us.status_code == 200 and r_us.json() == {"country": "US", "usd": 27.5}


def test_unknown_country_is_404():
    shipping = fresh()
    shipping.carrier_quote = lambda c: shipping.RATES.get(c)
    (r,) = run(get_all(shipping.app, ["/quote/XX"]))
    (r2,) = run(get_all(shipping.app, ["/quote/XX/USD"]))
    assert (r.status_code, r2.status_code) == (404, 404)


def test_quotes_are_served_concurrently():
    shipping = fresh()
    install_barrier_carrier(shipping)
    r1, r2 = run(get_all(shipping.app, ["/quote/DE", "/quote/IR"]))
    assert (r1.status_code, r2.status_code) == (200, 200), "the two requests could not overlap: the event loop was blocked"


def test_converted_quotes_are_served_concurrently():
    shipping = fresh()
    install_barrier_carrier(shipping)
    r1, r2 = run(get_all(shipping.app, ["/quote/DE/USD", "/quote/IR/EUR"]))
    assert (r1.status_code, r2.status_code) == (200, 200), "the two requests could not overlap: the event loop was blocked"
    assert r2.json() == {"country": "IR", "eur": 30.0}


def test_sdk_never_runs_on_the_loop_thread():
    shipping = fresh()
    loop_thread, seen = install_barrier_carrier(shipping, parties=1)
    run(get_all(shipping.app, ["/quote/DE", "/quote/DE/EUR"]))
    assert seen and loop_thread not in seen, "carrier_quote ran on the event loop's thread"
