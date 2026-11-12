import pytest
from fastapi.testclient import TestClient

import security
from app import User, create_app

TEST_SECRET = "t" * 32


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    monkeypatch.setenv("CHAT_JWT_SECRET", TEST_SECRET)
    monkeypatch.setattr(security, "ITERATIONS", 1_000)  # fast hashing in tests


@pytest.fixture
def users():
    return {
        "ali": User(id=1, username="ali", password_hash=security.hash_password("s3cret-pass")),
        "sara": User(id=2, username="sara", password_hash=security.hash_password("other-pass"), disabled=True),
    }


@pytest.fixture
def client(users):
    with TestClient(create_app(users)) as test_client:
        yield test_client


def login(client, username="ali", password="s3cret-pass"):
    """Log in the OAuth2 way: username and password as form fields (data=), not JSON."""
    return client.post("/auth/token", data={"username": username, "password": password})
