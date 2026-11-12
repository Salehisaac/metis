# Don't edit this file: fix messages_api.py until every test passes.
import importlib
import sys

from fastapi.testclient import TestClient


def client():
    """Import messages_api fresh, so each test starts with the two original messages."""
    sys.modules.pop("messages_api", None)
    return TestClient(importlib.import_module("messages_api").app)


def test_send_message_returns_201():
    c = client()
    r = c.post("/messages", json={"chat_id": 10, "text": "lunch?"})
    assert r.status_code == 201, r.text
    assert r.json() == {"id": 3, "chat_id": 10, "text": "lunch?", "pinned": False}


def test_read_existing_message():
    c = client()
    r = c.get("/messages/2")
    assert (r.status_code, r.json()["text"]) == (200, "standup at 10")


def test_read_missing_message_is_404():
    c = client()
    r = c.get("/messages/99")
    assert r.status_code == 404, r.text
    assert r.json() == {"detail": "message not found"}


def test_pinned_messages():
    c = client()
    r = c.get("/messages/pinned")
    assert r.status_code == 200, r.text
    assert [m["id"] for m in r.json()] == [2]


def test_edit_text_from_json_body():
    c = client()
    r = c.put("/messages/1/text", json={"text": "hi all"})
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "hi all"
    assert c.get("/messages/1").json()["text"] == "hi all"


def test_edit_missing_message_is_404():
    c = client()
    r = c.put("/messages/99/text", json={"text": "x"})
    assert (r.status_code, r.json()) == (404, {"detail": "message not found"})


def test_edit_without_text_is_422_from_body():
    c = client()
    r = c.put("/messages/1/text", json={})
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["body", "text"]


def test_delete_then_404():
    c = client()
    r = c.delete("/messages/1")
    assert (r.status_code, r.content) == (204, b"")
    r = c.delete("/messages/1")
    assert r.status_code == 404
    assert r.json() == {"detail": "message not found"}
