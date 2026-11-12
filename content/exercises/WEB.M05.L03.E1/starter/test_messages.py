"""Tests for the messages API. Don't edit this file: write the fixtures in conftest.py."""

from sqlalchemy import func, select
from sqlalchemy.pool import StaticPool

from app import Chat, Message, User


def add_chat_and_user(db):
    db.add_all([User(id=1, username="ali"), Chat(id=1, title="general")])
    db.commit()


def test_send_message_is_saved(client, db):
    add_chat_and_user(db)

    response = client.post("/chats/1/messages", json={"sender_id": 1, "text": "hi"})

    assert response.status_code == 201, response.text
    assert db.scalars(select(Message.text)).all() == ["hi"]


def test_send_to_unknown_chat_is_404(client):
    response = client.post("/chats/1/messages", json={"sender_id": 1, "text": "hi"})

    assert response.status_code == 404
    assert response.json() == {"detail": "chat not found"}


def test_unknown_sender_is_404(client, db):
    db.add(Chat(id=1, title="general"))
    db.commit()

    response = client.post("/chats/1/messages", json={"sender_id": 99, "text": "hi"})

    assert response.status_code == 404
    assert response.json() == {"detail": "sender not found"}


def test_list_messages_in_order(client, db):
    add_chat_and_user(db)
    client.post("/chats/1/messages", json={"sender_id": 1, "text": "first"})
    client.post("/chats/1/messages", json={"sender_id": 1, "text": "second"})

    response = client.get("/chats/1/messages")

    assert [m["text"] for m in response.json()] == ["first", "second"]


def test_database_starts_empty(db):
    assert db.scalar(select(func.count()).select_from(User)) == 0
    assert db.scalar(select(func.count()).select_from(Message)) == 0


def test_engine_is_in_memory_with_one_shared_connection(engine):
    assert engine is not None, "write the engine fixture"
    assert engine.url.database in (None, "", ":memory:"), "use an in-memory database"
    assert isinstance(engine.pool, StaticPool)
