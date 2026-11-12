import functools


def retry(times, exceptions=(Exception,)):
    """Decorator factory: call the function up to `times` times in total.

    @retry(3, exceptions=(ConnectionError,))
    def fetch(url): ...

    - Retry only when the exception is an instance of one of `exceptions`; anything else propagates at once.
    - After the last failed attempt, re-raise that last exception.
    - times < 1 raises ValueError immediately, when retry(...) is called.
    """
    if times < 1:
        raise ValueError(f"times must be at least 1, got {times}")

    def decorate(func):
        @functools.wraps(func)
        def call_with_retry(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == times:
                        raise

        return call_with_retry

    return decorate
