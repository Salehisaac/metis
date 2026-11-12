"""Fixtures for test_messages.py. This is the file you fix.

The tests pass one by one (pytest test_messages.py::test_new_chat_has_no_messages)
but fail when the whole file runs. Find out what leaks from one test into the next.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import create_app, get_clock

FROZEN = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)

shared_app = create_app()


@pytest.fixture
def app():
    return shared_app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def frozen_clock(app):
    """Make every message's sent_at equal FROZEN."""
    app.dependency_overrides[get_clock] = lambda: (lambda: FROZEN)
    return FROZEN
