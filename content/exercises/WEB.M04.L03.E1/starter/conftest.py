from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


def make_client(api):
    """A TestClient for a fresh app built from the module `api`.

    Chats 1 and 2 exist. Chat 1 already has one message, with id 1. Chat 2 has none.
    """
    app = api.create_app()
    seeded = api.MessageOut(id=1, chat_id=1, text="seed", sent_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    app.state.store.messages.append(seeded)
    app.state.store.next_id = 2
    return TestClient(app)


@pytest.fixture
def client():
    import app as api

    return make_client(api)
