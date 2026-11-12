"""Reference failure-path tests for the send-message unit of work."""

from sqlalchemy import func, select

from app import AuditEntry, AuditUnavailable, Chat, Message, get_audit


def rows(db, model):
    return db.scalar(select(func.count()).select_from(model))


def snapshot(db):
    db.expire_all()  # forget cached objects; read the database again
    return {
        "messages": rows(db, Message),
        "audit": rows(db, AuditEntry),
        "count": db.get(Chat, 1).message_count,
    }


def test_send_saves_message_count_and_audit(client, db):
    response = client.post("/chats/1/messages", json={"client_id": "m-1", "text": "hello"})

    assert response.status_code == 201, response.text
    assert response.json() == {"id": 1, "chat_id": 1, "text": "hello"}
    assert snapshot(db) == {"messages": 1, "audit": 1, "count": 1}


def test_duplicate_client_id_is_409_and_changes_nothing(client, db):
    client.post("/chats/1/messages", json={"client_id": "m-1", "text": "hello"})
    before = snapshot(db)

    response = client.post("/chats/1/messages", json={"client_id": "m-1", "text": "hello again"})

    assert response.status_code == 409
    assert snapshot(db) == before


def test_audit_failure_rolls_back_everything(client, db):
    class BrokenAudit:
        def record(self, session, action):
            raise AuditUnavailable()

    client.app.dependency_overrides[get_audit] = BrokenAudit

    response = client.post("/chats/1/messages", json={"client_id": "m-1", "text": "hello"})

    assert response.status_code == 503
    assert snapshot(db) == {"messages": 0, "audit": 0, "count": 0}


def test_no_connection_is_held_after_requests(client, connections):
    client.post("/chats/1/messages", json={"client_id": "m-1", "text": "hello"})
    client.post("/chats/99/messages", json={"client_id": "m-2", "text": "nobody"})
    client.post("/chats/1/messages", json={"client_id": "m-1", "text": "again"})

    assert connections.checkouts > 0
    assert connections.checked_out() == 0
