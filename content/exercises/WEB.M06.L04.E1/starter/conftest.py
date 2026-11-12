import pytest
from fastapi.testclient import TestClient

import security
from app import Chat, Message, Store, User, create_app

ALI, SARA, MOD, ROOT, MOD2 = 1, 2, 3, 4, 5


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("CHAT_JWT_SECRET", "t" * 32)


@pytest.fixture
def store():
    return Store(
        users={
            ALI: User(ALI, "ali"),
            SARA: User(SARA, "sara"),
            MOD: User(MOD, "mod", role="moderator"),
            ROOT: User(ROOT, "root", role="admin"),
            MOD2: User(MOD2, "mod2", role="moderator"),
        },
        chats={1: Chat(1, "general", {ALI, SARA}), 2: Chat(2, "mods", {MOD, MOD2})},
        messages={1: Message(1, 1, ALI, "hi all"), 2: Message(2, 1, SARA, "hey ali")},
    )


@pytest.fixture
def client(store):
    with TestClient(create_app(store)) as test_client:
        yield test_client


def auth(user_id):
    """Headers for a request as user_id; None means no Authorization header at all."""
    if user_id is None:
        return {}
    return {"Authorization": f"Bearer {security.create_access_token(user_id)}"}
