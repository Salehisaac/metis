```python
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import create_app, get_clock

FROZEN = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def app():
    application = create_app()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def frozen_clock(app):
    """Make every message's sent_at equal FROZEN."""
    app.dependency_overrides[get_clock] = lambda: (lambda: FROZEN)
    yield FROZEN
    del app.dependency_overrides[get_clock]
```

**Why the starter failed only in a full run**

- `shared_app = create_app()` ran once, when pytest imported `conftest.py`. Every test got the same app and therefore the same `Store`. `test_post_then_list` left a message behind, so the next test saw one message instead of none, and the next id was 2 instead of 1.
- `frozen_clock` put an override into `dependency_overrides` and never removed it. The test after it still had the frozen clock, so its `sent_at` was in 2026-01-01, before "now".
- Run alone, each test was the first and only user of the shared app. That's why "passes alone, fails together" almost always means **shared state between tests**.

**Why the fix works**

- `app` is function-scoped (the default), so `create_app()` runs once per test: a new `Store` every time. pytest also caches a fixture within one test, so `client` and `frozen_clock` get the **same** app object as the test does.
- Code after `yield` is teardown: it runs after the test, even when the test fails. The overrides are removed there, so nothing leaks even if someone later makes the app fixture shared.
- `with TestClient(app)` also runs the app's lifespan (startup/shutdown), which a real app needs for things like opening a database pool.

**Alternative:** set `app.dependency_overrides = {}` in teardown, as the FastAPI docs show. `clear()` does the same thing on the existing dict.
