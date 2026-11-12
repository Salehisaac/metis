import asyncio


def run(coro):
    async def bounded():
        async with asyncio.timeout(5):
            return await coro
    return asyncio.run(bounded())


async def fast(conn, query):
    await asyncio.sleep(0.01)
    return f"{query} on {conn}"


async def slow(conn, query):
    await asyncio.sleep(1)
    return "too late"


async def broken(conn, query):
    await asyncio.sleep(0.01)
    raise ValueError("syntax error")


def test_run_query_success_releases():
    import lease
    pool = lease.Pool()
    assert run(lease.run_query(pool, "SELECT 1", fast)) == "SELECT 1 on conn-1"
    assert pool.leased == 0


def test_run_query_error_releases():
    import lease
    pool = lease.Pool()
    try:
        run(lease.run_query(pool, "SELEC 1", broken))
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError should propagate")
    assert pool.leased == 0, "connection leaked after an error"


def test_fast_query_returns_result():
    import lease
    pool = lease.Pool()
    assert run(lease.query_or_default(pool, "SELECT 1", fast, seconds=1, default="dflt")) == "SELECT 1 on conn-1"
    assert pool.leased == 0


def test_slow_query_returns_default_and_releases():
    import lease
    pool = lease.Pool()
    assert run(lease.query_or_default(pool, "SELECT big", slow, seconds=0.05, default="dflt")) == "dflt"
    assert pool.leased == 0, "connection leaked after a timeout"


def test_query_error_is_not_a_timeout():
    import lease
    pool = lease.Pool()
    try:
        run(lease.query_or_default(pool, "SELEC 1", broken, seconds=1, default="dflt"))
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError should propagate, not become the default")
    assert pool.leased == 0


def test_cancellation_propagates_and_releases():
    import lease
    pool = lease.Pool()

    async def scenario():
        task = asyncio.create_task(lease.query_or_default(pool, "SELECT big", slow, seconds=5, default="dflt"))
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            result = await task
        except asyncio.CancelledError:
            return "cancelled", task.cancelled()
        return result, task.cancelled()

    assert run(scenario()) == ("cancelled", True), "the cancellation was swallowed"
    assert pool.leased == 0, "connection leaked after cancellation"
