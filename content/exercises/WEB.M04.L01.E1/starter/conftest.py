import pytest
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture
def client():
    """A TestClient for a fresh app: chats 1 and 2 exist, no messages yet."""
    return TestClient(create_app())
