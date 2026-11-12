"""Fixtures for test_messages.py: a fresh app per test, cleanup after every test."""

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
