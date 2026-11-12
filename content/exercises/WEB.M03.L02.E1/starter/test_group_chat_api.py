import importlib
import sys

import pytest
from fastapi.testclient import TestClient

ALI = {"X-User-Id": "1"}
OMID = {"X-User-Id": "3"}


def load():
    sys.modules.pop("group_chat_api", None)
    module = importlib.import_module("group_chat_api")
    return TestClient(module.app), module


def balanced(module):
    """Every transaction that began was closed."""
    return module.tx_log.count("begin") == module.tx_log.count("close")


def test_missing_or_unknown_user_is_401():
    c, module = load()
    for headers in [{}, {"X-User-Id": "42"}]:
        r = c.post("/chats/10/messages", json={"text": "hi"}, headers=headers)
        assert r.status_code == 401, f"{headers}: {r.text}"
        assert r.json() == {"detail": "missing or unknown X-User-Id"}
    assert module.MESSAGES == []


def test_non_integer_user_id_is_422():
    c, _ = load()
    r = c.get("/chats/10/messages", headers={"X-User-Id": "ali"})
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["header", "x-user-id"]


def test_member_sends_and_transaction_commits_and_closes():
    c, module = load()
    r = c.post("/chats/10/messages", json={"text": "standup?"}, headers=ALI)
    assert r.status_code == 201, r.text
    assert r.json() == {"chat_id": 10, "sender_id": 1, "text": "standup?"}
    assert module.MESSAGES == [r.json()]
    assert module.tx_log == ["begin", "commit", "close"]


def test_non_member_is_403_and_nothing_stored():
    c, module = load()
    r = c.post("/chats/10/messages", json={"text": "let me in"}, headers=OMID)
    assert r.status_code == 403
    assert r.json() == {"detail": "not a member of this chat"}
    assert c.get("/chats/10/messages", headers=OMID).status_code == 403
    assert module.MESSAGES == []
    assert balanced(module)


def test_unknown_chat_is_404_but_authentication_comes_first():
    c, module = load()
    r = c.get("/chats/99/messages", headers=ALI)
    assert (r.status_code, r.json()) == (404, {"detail": "chat not found"})
    assert c.get("/chats/99/messages").status_code == 401
    assert balanced(module)


def test_failed_batch_rolls_back_everything():
    c, module = load()
    r = c.post("/chats/10/messages/batch", json={"texts": ["one", "two", "  ", "four"]}, headers=ALI)
    assert r.status_code == 422
    assert module.MESSAGES == [], "messages added before the failure must not be stored"
    assert module.tx_log == ["begin", "rollback", "close"]


def test_successful_batch():
    c, module = load()
    r = c.post("/chats/10/messages/batch", json={"texts": ["one", "two"]}, headers=ALI)
    assert (r.status_code, r.json()) == (201, {"sent": 2})
    assert [m["text"] for m in c.get("/chats/10/messages", headers=ALI).json()] == ["one", "two"]
    assert balanced(module)


def test_unexpected_error_is_rolled_back_and_re_raised():
    c, module = load()
    with pytest.raises(RuntimeError, match="simulated bug"):
        c.post("/debug/crash")
    assert module.MESSAGES == []
    assert module.tx_log == ["begin", "rollback", "close"]


def test_current_user_can_be_overridden_in_tests():
    c, module = load()
    module.app.dependency_overrides[module.get_current_user] = lambda: module.USERS[2]
    r = c.post("/chats/10/messages", json={"text": "no header needed"})
    assert (r.status_code, r.json()["sender_id"]) == (201, 2)
    module.app.dependency_overrides = {}
    assert c.post("/chats/10/messages", json={"text": "x"}).status_code == 401
