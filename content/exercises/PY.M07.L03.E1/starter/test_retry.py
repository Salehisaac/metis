import pytest


def flaky(failures, exc=ConnectionError):
    """A function that fails `failures` times, then returns 'ok'. calls[0] counts the calls."""
    calls = [0]

    def fetch():
        """Fetch something over the network."""
        calls[0] += 1
        if calls[0] <= failures:
            raise exc(f"attempt {calls[0]}")
        return "ok"

    return fetch, calls


def test_success_first_time_calls_once():
    from retry import retry
    fetch, calls = flaky(0)
    assert retry(3)(fetch)() == "ok"
    assert calls[0] == 1


def test_retries_until_success():
    from retry import retry
    fetch, calls = flaky(2)
    assert retry(3)(fetch)() == "ok"
    assert calls[0] == 3


def test_reraises_last_error_after_all_attempts():
    from retry import retry
    fetch, calls = flaky(10)
    with pytest.raises(ConnectionError, match="attempt 3"):
        retry(3)(fetch)()
    assert calls[0] == 3


def test_times_one_means_no_retry():
    from retry import retry
    fetch, calls = flaky(1)
    with pytest.raises(ConnectionError, match="attempt 1"):
        retry(1)(fetch)()
    assert calls[0] == 1


def test_other_exceptions_are_not_retried():
    from retry import retry
    fetch, calls = flaky(1, exc=ValueError)
    with pytest.raises(ValueError):
        retry(3, exceptions=(ConnectionError,))(fetch)()
    assert calls[0] == 1


def test_subclasses_count_as_listed_exceptions():
    from retry import retry
    fetch, calls = flaky(2, exc=ConnectionError)   # ConnectionError is a subclass of OSError
    assert retry(3, exceptions=(OSError,))(fetch)() == "ok"
    assert calls[0] == 3


def test_passes_arguments_and_returns_result():
    from retry import retry

    @retry(2)
    def price(amount, *, tax=0.0, currency="EUR"):
        return f"{amount * (1 + tax):.2f} {currency}"

    assert price(10, tax=0.5) == "15.00 EUR"
    assert price(4, currency="USD") == "4.00 USD"


def test_each_call_gets_fresh_attempts():
    from retry import retry
    calls = [0]

    @retry(2)
    def every_other():
        calls[0] += 1
        if calls[0] % 2 == 1:
            raise ConnectionError("odd call")
        return calls[0]

    assert every_other() == 2
    assert every_other() == 4, "the attempt count must restart for every call"


def test_keeps_name_and_docstring():
    from retry import retry
    fetch, _ = flaky(0)
    wrapped = retry(3)(fetch)
    assert wrapped.__name__ == "fetch"
    assert wrapped.__doc__ == "Fetch something over the network."
    assert wrapped.__wrapped__ is fetch


def test_times_must_be_positive():
    from retry import retry
    with pytest.raises(ValueError):
        retry(0)
    with pytest.raises(ValueError):
        retry(-1)
