"""Tests for the messages API. Don't edit this file: fix conftest.py instead."""

from datetime import datetime, timezone


def test_post_then_list(client):
    client.post("/chats/1/messages", json={"text": "hello"})

    response = client.get("/chats/1/messages")

    assert [m["text"] for m in response.json()] == ["hello"]


def test_new_chat_has_no_messages(client):
    response = client.get("/chats/1/messages")

    assert response.status_code == 200
    assert response.json() == []


def test_first_message_gets_id_1(client):
    response = client.post("/chats/2/messages", json={"text": "hi"})

    assert response.json()["id"] == 1


def test_sent_at_comes_from_the_clock(client, frozen_clock):
    response = client.post("/chats/1/messages", json={"text": "standup"})

    assert response.status_code == 201
    assert response.json()["sent_at"] == "2026-01-01T09:00:00Z"


def test_real_clock_is_used_without_the_fixture(client):
    before = datetime.now(timezone.utc)

    response = client.post("/chats/1/messages", json={"text": "now"})

    sent_at = datetime.fromisoformat(response.json()["sent_at"])
    assert sent_at >= before


def test_fixture_gives_a_fresh_app(app):
    assert app.state.store.messages == []
    assert app.dependency_overrides == {}
