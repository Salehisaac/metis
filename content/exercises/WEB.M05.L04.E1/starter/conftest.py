"""Fixtures for YOUR tests. Don't edit this file.

Every test gets a fresh SQLite FILE database (so each session has its own connection,
like a real server) with one chat: id 1, title "general", message_count 0.
"""

import gc

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session


class Connections:
    """Counts pool checkouts and checkins on an engine."""

    def __init__(self, engine):
        self.checkouts = 0
        self.checkins = 0
        event.listen(engine, "checkout", self._out)
        event.listen(engine, "checkin", self._in)

    def _out(self, *args):
        self.checkouts += 1

    def _in(self, *args):
        self.checkins += 1

    def checked_out(self):
        """Connections that are still held by someone."""
        return self.checkouts - self.checkins


def make_engine(api, path):
    engine = create_engine(f"sqlite:///{path}")
    api.Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(api.Chat(id=1, title="general"))
        session.commit()
    return engine


@pytest.fixture
def engine(tmp_path):
    import app as api

    eng = make_engine(api, tmp_path / "test.db")
    yield eng
    eng.dispose()


@pytest.fixture
def connections(engine):
    """Counts connections. The garbage collector is paused meanwhile, because it could quietly
    reclaim a leaked session (and its connection) and hide the leak from the test."""
    gc.disable()
    yield Connections(engine)
    gc.enable()


@pytest.fixture
def db(engine):
    """A separate session for Arrange and Assert. Every query sees committed data only."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine):
    import app as api

    with TestClient(api.create_app(engine)) as test_client:
        yield test_client
