import asyncio


def run(coro):
    async def bounded():
        async with asyncio.timeout(5):
            return await coro
    return asyncio.run(bounded())


class FakeQuoteAPI:
    """Async fake that records how many calls are in flight at the same time."""

    def __init__(self, delays=None):
        self.delays = delays or {}
        self.calls = []
        self.in_flight = 0
        self.peak = 0

    async def __call__(self, symbol):
        self.calls.append(symbol)
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            await asyncio.sleep(self.delays.get(symbol, 0.05))
        finally:
            self.in_flight -= 1
        return float(len(symbol))


def test_returns_all_quotes():
    import quotes
    api = FakeQuoteAPI()
    assert run(quotes.fetch_quotes(["AAPL", "GOOG", "MSFT"], api)) == {"AAPL": 4.0, "GOOG": 4.0, "MSFT": 4.0}


def test_lookups_run_concurrently():
    import quotes
    api = FakeQuoteAPI()
    run(quotes.fetch_quotes(["A", "BB", "CCC", "DDDD"], api))
    assert api.peak == 4, f"at most {api.peak} lookup(s) were in flight at once; expected all 4"


def test_order_follows_input_not_finish_time():
    import quotes
    api = FakeQuoteAPI(delays={"SLOW": 0.15, "FAST": 0.01, "MID": 0.05})
    result = run(quotes.fetch_quotes(["SLOW", "FAST", "MID"], api))
    assert list(result) == ["SLOW", "FAST", "MID"]


def test_duplicates_fetched_once():
    import quotes
    api = FakeQuoteAPI()
    result = run(quotes.fetch_quotes(["IBM", "IBM", "SAP", "IBM"], api))
    assert sorted(api.calls) == ["IBM", "SAP"]
    assert list(result) == ["IBM", "SAP"]


def test_empty_list():
    import quotes
    api = FakeQuoteAPI()
    assert run(quotes.fetch_quotes([], api)) == {}
    assert api.calls == []
