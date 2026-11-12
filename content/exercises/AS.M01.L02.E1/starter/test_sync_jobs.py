import asyncio


def run(coro):
    async def bounded():
        async with asyncio.timeout(5):  # a stuck loop fails the test instead of hanging
            return await coro
    return asyncio.run(bounded())


def test_pulls_interleave():
    import sync_jobs

    async def main():
        log = []
        a = asyncio.create_task(sync_jobs.pull_pages("a", 3, log))
        b = asyncio.create_task(sync_jobs.pull_pages("b", 3, log))
        await a
        await b
        return log

    log = run(main())
    assert sorted(log) == ["a0", "a1", "a2", "b0", "b1", "b2"]
    assert log.index("b0") < log.index("a1"), f"b never started while a was waiting: {log}"


def test_pull_zero_pages():
    import sync_jobs
    log = []
    run(sync_jobs.pull_pages("a", 0, log))
    assert log == []


async def _ticker(log, stop):
    while not stop.is_set():
        log.append("tick")
        await asyncio.sleep(0)


async def _checksum_with_ticker(sync_jobs, rows, every):
    log, stop = [], asyncio.Event()
    t = asyncio.create_task(_ticker(log, stop))
    total = await sync_jobs.checksum(rows, log, every)
    stop.set()
    await t
    return total, log


def test_checksum_lets_others_run():
    import sync_jobs
    rows = [f"row-{i}" for i in range(1000)]
    _, log = run(_checksum_with_ticker(sync_jobs, rows, 100))
    ticks_before_done = log.index("checksum done")
    assert ticks_before_done >= 5, f"other tasks ran only {ticks_before_done} times during checksum"


def test_checksum_value_unchanged():
    import sync_jobs
    rows = ["abc", "", "héllo", "x" * 300] * 60
    expected = sum(sum(r.encode()) for r in rows)
    total, _ = run(_checksum_with_ticker(sync_jobs, rows, 7))
    assert total == expected


def test_checksum_empty_rows():
    import sync_jobs
    total, log = run(_checksum_with_ticker(sync_jobs, [], 100))
    assert total == 0
    assert "checksum done" in log


def test_checksum_rejects_bad_every():
    import sync_jobs
    for bad in (0, -1):
        try:
            run(sync_jobs.checksum(["a"], [], bad))
        except ValueError:
            continue
        raise AssertionError(f"checksum(..., every={bad}) should raise ValueError")
