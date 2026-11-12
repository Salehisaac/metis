```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import Base, create_app


@pytest.fixture
def engine():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine):
    with TestClient(create_app(engine)) as test_client:
        yield test_client
```

**Why each piece is needed**

- **`sqlite://`** is an in-memory database. It's fast and disappears with its connection, so every test starts empty without any cleanup SQL.
- **`poolclass=StaticPool`:** an in-memory database lives inside one connection. FastAPI runs `def` endpoints in worker threads, and SQLite's default pool for `:memory:` gives each thread its own connection, so the app would see a different, empty database: `no such table: chats`. StaticPool hands every checkout the same single connection.
- **`check_same_thread=False`:** that single connection was created in the test's thread and is then used from the app's worker thread. Python's `sqlite3` refuses that by default with "SQLite objects created in a thread can only be used in that same thread".
- **`create_all` per test:** the tables are created on the fresh database. In production, Alembic migrations create them (DB.M07). Running the migrations in tests is the stricter option, because it also tests the migrations.
- **`create_app(engine)`** instead of the module-level `app`: the factory takes the engine as a parameter, so tests choose the database without touching the app's code. That's dependency injection by constructor, as you'd do in Go.

**Limitation to remember:** with StaticPool, the test's `db` session and the app's sessions share one connection, so they also share its transaction state. A test can then see rows the app flushed but never committed. For tests about commits and rollbacks, use a temporary file database instead (next lesson).

**Alternative:** keep the production `get_session` and replace it with `app.dependency_overrides[get_session] = ...` (the FastAPI docs' approach). That works with any app structure, but you must remember to override every place that creates sessions.
