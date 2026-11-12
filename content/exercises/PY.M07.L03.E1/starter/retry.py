import functools


def retry(times, exceptions=(Exception,)):
    """Decorator factory: call the function up to `times` times in total.

    @retry(3, exceptions=(ConnectionError,))
    def fetch(url): ...

    - Retry only when the exception is an instance of one of `exceptions`; anything else propagates at once.
    - After the last failed attempt, re-raise that last exception.
    - times < 1 raises ValueError immediately, when retry(...) is called.
    """
    raise NotImplementedError
