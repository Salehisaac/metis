import importlib
import sys

from fastapi.testclient import TestClient


def client():
    """Import chats_api fresh, so each test starts with no chats."""
    sys.modules.pop("chats_api", None)
    return TestClient(importlib.import_module("chats_api").app)


def test_create_returns_201_location_and_chat():
    c = client()
    r = c.post("/chats", json={"title": "Backend team"})
    assert r.status_code == 201, r.text
    assert r.json() == {"id": 1, "title": "Backend team"}
    assert r.headers.get("location") == "/chats/1"
    r = c.post("/chats", json={"title": "Family"})
    assert (r.status_code, r.headers.get("location")) == (201, "/chats/2")


def test_duplicate_title_is_409_case_insensitive():
    c = client()
    c.post("/chats", json={"title": "Backend team"})
    for title in ["Backend team", "backend TEAM"]:
        r = c.post("/chats", json={"title": title})
        assert r.status_code == 409, f"{title!r}: {r.text}"
        assert r.json() == {"detail": "chat title already taken"}


def test_missing_title_is_422():
    c = client()
    assert c.post("/chats", json={}).status_code == 422
    assert c.post("/chats", json={"name": "x"}).status_code == 422


def test_read_existing_and_missing():
    c = client()
    c.post("/chats", json={"title": "Family"})
    r = c.get("/chats/1")
    assert (r.status_code, r.json()) == (200, {"id": 1, "title": "Family"})
    r = c.get("/chats/2")
    assert r.status_code == 404
    assert r.json() == {"detail": "chat not found"}


def test_put_renames():
    c = client()
    c.post("/chats", json={"title": "Family"})
    r = c.put("/chats/1", json={"title": "Family 2026"})
    assert (r.status_code, r.json()) == (200, {"id": 1, "title": "Family 2026"})
    assert c.get("/chats/1").json()["title"] == "Family 2026"


def test_put_same_title_twice_is_idempotent():
    c = client()
    c.post("/chats", json={"title": "Family"})
    for _ in range(2):
        r = c.put("/chats/1", json={"title": "Family"})
        assert r.status_code == 200, "renaming a chat to its own title is not a conflict"
    r = c.put("/chats/1", json={"title": "FAMILY"})
    assert (r.status_code, r.json()["title"]) == (200, "FAMILY")


def test_put_to_another_chats_title_is_409():
    c = client()
    c.post("/chats", json={"title": "Family"})
    c.post("/chats", json={"title": "Work"})
    r = c.put("/chats/2", json={"title": "family"})
    assert r.status_code == 409
    assert r.json() == {"detail": "chat title already taken"}
    assert c.get("/chats/2").json()["title"] == "Work", "a rejected rename must not change the chat"


def test_put_missing_chat_is_404():
    c = client()
    r = c.put("/chats/7", json={"title": "Ghost"})
    assert (r.status_code, r.json()) == (404, {"detail": "chat not found"})


def test_delete_is_204_then_404():
    c = client()
    c.post("/chats", json={"title": "Family"})
    r = c.delete("/chats/1")
    assert r.status_code == 204
    assert r.content == b"", "a 204 response has no body"
    assert c.get("/chats/1").status_code == 404
    r = c.delete("/chats/1")
    assert (r.status_code, r.json()) == (404, {"detail": "chat not found"})


def test_ids_are_not_reused_and_titles_free_up():
    c = client()
    c.post("/chats", json={"title": "A"})
    c.post("/chats", json={"title": "B"})
    c.delete("/chats/2")
    r = c.post("/chats", json={"title": "B"})
    assert r.status_code == 201, "a deleted chat's title is free again"
    assert r.json()["id"] == 3, "ids are never reused"
