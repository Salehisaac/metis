"""Test database fixtures. This is the file you write."""

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def engine():
    """TODO: a new in-memory SQLite engine for each test, with all tables created."""
    return None


@pytest.fixture
def db(engine):
    """TODO: a Session on the test engine for arranging and checking data, closed after the test."""
    return None


@pytest.fixture
def client(engine):
    """TODO: a TestClient for an app that uses the test engine."""
    return TestClient(app)
