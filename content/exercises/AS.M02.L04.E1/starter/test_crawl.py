import asyncio


def run(coro):
    async def bounded():
        async with asyncio.timeout(5):
            return await coro
    return asyncio.run(bounded())


class FakeSite:
    def __init__(self):
        self.in_flight = 0
        self.peak = 0
        self.calls = 0

    async def __call__(self, url):
        self.calls += 1
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            await asyncio.sleep(0.01 * (len(url) % 4 + 1))  # different durations
            if url == "/boom":
                raise ConnectionError(url)
        finally:
            self.in_flight -= 1
        return f"<{url}>"


URLS = [f"/page{i}" for i in range(12)]


def test_results_in_input_order():
    import crawl
    site = FakeSite()
    urls = ["/a", "/bbbb", "/cc", "/ddd"]
    assert run(crawl.fetch_many(urls, site, limit=2)) == ["</a>", "</bbbb>", "</cc>", "</ddd>"]


def test_never_more_than_limit():
    import crawl
    site = FakeSite()
    run(crawl.fetch_many(URLS, site, limit=3))
    assert site.calls == 12
    assert site.peak <= 3, f"{site.peak} fetches ran at once with limit=3"


def test_uses_the_whole_limit():
    import crawl
    site = FakeSite()
    run(crawl.fetch_many(URLS, site, limit=3))
    assert site.peak == 3, f"only {site.peak} fetch(es) ran at once; limit=3 allows 3"


def test_limit_larger_than_work():
    import crawl
    site = FakeSite()
    assert len(run(crawl.fetch_many(URLS[:4], site, limit=100))) == 4
    assert site.peak == 4


def test_limit_one_is_sequential():
    import crawl
    site = FakeSite()
    run(crawl.fetch_many(URLS[:5], site, limit=1))
    assert site.peak == 1


def test_empty_list():
    import crawl
    site = FakeSite()
    assert run(crawl.fetch_many([], site, limit=3)) == []
    assert site.calls == 0


def test_bad_limit():
    import crawl
    for bad in (0, -2):
        try:
            run(crawl.fetch_many(URLS, FakeSite(), limit=bad))
        except ValueError:
            continue
        raise AssertionError(f"limit={bad} should raise ValueError")


def test_fetch_error_propagates():
    import crawl
    site = FakeSite()

    async def scenario():
        caught = None
        try:
            await crawl.fetch_many(["/ok", "/boom", "/fine"], site, limit=2)
        except* ConnectionError as eg:  # (return isn't allowed inside except*)
            caught = [str(e) for e in eg.exceptions]
        return caught

    assert run(scenario()) == ["/boom"]
