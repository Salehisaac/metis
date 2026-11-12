import importlib
import sys

from fastapi.testclient import TestClient


def client():
    """Import messages_api fresh, so each test starts from the original data."""
    sys.modules.pop("messages_api", None)
    module = importlib.import_module("messages_api")
    return TestClient(module.app), module


def ids(response):
    assert response.status_code == 200, response.text
    return [m["id"] for m in response.json()["messages"]]


def test_lists_chat_messages_newest_first():
    c, _ = client()
    r = c.get("/chats/10/messages")
    assert r.status_code == 200, r.text
    assert r.json()["chat_id"] == 10, "chat_id must be returned as an int"
    assert ids(r) == [5, 4, 2, 1]
    assert r.json()["messages"][0] == {"id": 5, "chat_id": 10, "sender": "sara", "text": "fine", "read": False}


def test_limit_applies_after_sorting():
    c, _ = client()
    assert ids(c.get("/chats/10/messages?limit=2")) == [5, 4]


def test_before_is_exclusive():
    c, _ = client()
    assert ids(c.get("/chats/10/messages?before=4")) == [2, 1]


def test_before_and_limit_combine():
    c, _ = client()
    assert ids(c.get("/chats/10/messages?before=5&limit=1")) == [4]


def test_unread_only_accepts_bool_spellings():
    c, _ = client()
    assert ids(c.get("/chats/10/messages?unread_only=true")) == [5, 4]
    assert ids(c.get("/chats/10/messages?unread_only=yes&limit=1")) == [5]
    assert ids(c.get("/chats/10/messages?unread_only=false")) == [5, 4, 2, 1]


def test_chat_without_messages_gives_empty_list():
    c, _ = client()
    r = c.get("/chats/99/messages")
    assert r.status_code == 200, r.text
    assert r.json() == {"chat_id": 99, "messages": []}


def test_limit_bounds():
    c, _ = client()
    assert c.get("/chats/10/messages?limit=0").status_code == 422
    assert c.get("/chats/10/messages?limit=101").status_code == 422
    assert c.get("/chats/10/messages?limit=100").status_code == 200
    assert c.get("/chats/10/messages?limit=1").status_code == 200


def test_bad_types_give_422():
    c, _ = client()
    r = c.get("/chats/ten/messages")
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["path", "chat_id"]
    r = c.get("/chats/10/messages?before=latest")
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["query", "before"]
    assert c.get("/chats/10/messages?unread_only=maybe").status_code == 422


def test_listing_does_not_reorder_the_data():
    c, module = client()
    c.get("/chats/10/messages")
    c.get("/chats/20/messages?unread_only=true")
    assert [m["id"] for m in module.MESSAGES] == [1, 2, 3, 4, 5, 6], "sort a copy, not MESSAGES itself"
