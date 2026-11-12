import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import Base, Chat, Member, Message, User, create_app


@pytest.fixture
def engine(tmp_path):
    """A fresh SQLite file database per test, with users 1 (ali) and 2 (sara)."""
    eng = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        session.add_all([User(id=1, username="ali"), User(id=2, username="sara")])
        session.commit()
    yield eng
    eng.dispose()


@pytest.fixture
def client(engine):
    """Answers like a real server: an unhandled error becomes a 500 response, not an exception."""
    return TestClient(create_app(engine), raise_server_exceptions=False)


@pytest.fixture
def counts(engine):
    """counts() -> committed rows per table, read through a separate session."""

    def read():
        with Session(engine) as session:
            return {
                model.__tablename__: session.scalar(select(func.count()).select_from(model))
                for model in (Chat, Member, Message)
            }

    return read
