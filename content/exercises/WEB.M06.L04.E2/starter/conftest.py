"""Shared setup. Don't edit this file.

Users: OLGA (1) owns chat 1; ALI (2) and SARA (3) are members of chat 1; ROOT (4) is an
admin and not a member; EVE (5) is an ordinary user and not a member. Chat 1 members: {1, 2, 3}.
"""

import pytest
from fastapi.testclient import TestClient

import security

OLGA, ALI, SARA, ROOT, EVE = 1, 2, 3, 4, 5
BAD_TOKEN = "bad-token"


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("CHAT_JWT_SECRET", "t" * 32)


def make_client(api):
    """A TestClient for a fresh app built from the module `api`, with the users and chat above."""
    store = api.Store(
        users={
            OLGA: api.User(OLGA, "olga"),
            ALI: api.User(ALI, "ali"),
            SARA: api.User(SARA, "sara"),
            ROOT: api.User(ROOT, "root", role="admin"),
            EVE: api.User(EVE, "eve"),
        },
        chats={1: api.Chat(1, "general", owner_id=OLGA, member_ids={OLGA, ALI, SARA})},
    )
    return TestClient(api.create_app(store))


def headers(actor):
    """None: no Authorization header. BAD_TOKEN: a garbage bearer token. A user id: a valid token."""
    if actor is None:
        return {}
    if actor == BAD_TOKEN:
        return {"Authorization": "Bearer not-a-jwt"}
    return {"Authorization": f"Bearer {security.create_access_token(actor)}"}


@pytest.fixture
def client():
    import app as api

    return make_client(api)
