import gc

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event

from app import Base, create_app


@pytest.fixture
def engine(tmp_path):
    """A fresh SQLite file database per test, with the tables created."""
    eng = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def connections(engine):
    """Counts pool checkouts and checkins. checked_out() is how many are still held."""

    class Counter:
        checkouts = 0
        checkins = 0

        def checked_out(self):
            return self.checkouts - self.checkins

    counter = Counter()

    def on_checkout(*args):
        counter.checkouts += 1

    def on_checkin(*args):
        counter.checkins += 1

    event.listen(engine, "checkout", on_checkout)
    event.listen(engine, "checkin", on_checkin)
    gc.disable()  # the garbage collector could reclaim a leaked session and hide the leak
    yield counter
    gc.enable()


@pytest.fixture
def client(engine):
    return TestClient(create_app(engine))
