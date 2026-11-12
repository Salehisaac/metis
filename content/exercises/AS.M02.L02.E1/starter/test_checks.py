import asyncio


def run(coro):
    async def bounded():
        async with asyncio.timeout(5):
            return await coro
    return asyncio.run(bounded())


def make_probe(finished):
    async def probe(host):
        await asyncio.sleep(0.05 if host != "slow" else 0.2)
        if host.startswith("bad"):
            raise ConnectionError(f"{host} refused")
        finished.append(host)
        return 200
    return probe


def test_report_all_up():
    import checks
    up, down = run(checks.health_report(["api", "web"], make_probe([])))
    assert up == {"api": 200, "web": 200}
    assert down == {}


def test_report_splits_failures():
    import checks
    up, down = run(checks.health_report(["api", "bad-db", "web"], make_probe([])))
    assert up == {"api": 200, "web": 200}
    assert list(down) == ["bad-db"]
    assert isinstance(down["bad-db"], ConnectionError)
    assert str(down["bad-db"]) == "bad-db refused"


def test_report_failure_does_not_stop_others():
    import checks
    finished = []
    run(checks.health_report(["bad-db", "slow"], make_probe(finished)))
    assert finished == ["slow"]


def test_report_empty():
    import checks
    assert run(checks.health_report([], make_probe([]))) == ({}, {})


def make_fetch(log):
    async def fetch(name):
        try:
            await asyncio.sleep(0.01 if name == "missing" else 0.3)
        except asyncio.CancelledError:
            log.append(f"cancelled {name}")
            raise
        if name == "missing":
            raise KeyError(name)
        return f"value of {name}"
    return fetch


def test_settings_all_present():
    import checks
    out = run(checks.load_settings(["db_url", "secret"], make_fetch([])))
    assert out == {"db_url": "value of db_url", "secret": "value of secret"}


def test_settings_failure_cancels_the_rest_first():
    import checks
    log = []

    async def scenario():
        try:
            await checks.load_settings(["db_url", "missing", "secret"], make_fetch(log))
        except BaseException as exc:
            return exc, list(log)  # snapshot the log at the moment the error arrives
        return None, list(log)

    exc, log_at_error = run(scenario())
    assert exc is not None, "load_settings should raise when a setting is missing"
    assert sorted(log_at_error) == ["cancelled db_url", "cancelled secret"], \
        f"other fetches were not cancelled before the error was raised: {log_at_error}"


def test_settings_error_arrives_in_exception_group():
    import checks

    async def scenario():
        try:
            await checks.load_settings(["missing", "secret"], make_fetch([]))
        except BaseException as exc:
            return exc

    exc = run(scenario())
    assert isinstance(exc, ExceptionGroup), f"expected an ExceptionGroup, got {exc!r}"
    assert [type(e) for e in exc.exceptions] == [KeyError]


def test_settings_empty():
    import checks
    assert run(checks.load_settings([], make_fetch([]))) == {}
