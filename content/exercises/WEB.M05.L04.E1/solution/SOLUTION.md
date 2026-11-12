```python
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
```

**Which test kills which mutant**

| Mutant | Killed by | Why |
|---|---|---|
| `commit_per_step` | `test_audit_failure_rolls_back_everything` | the message is committed before the audit fails, so `messages` is 1, not 0 |
| `conflict_is_500` | `test_duplicate_...` | the IntegrityError escapes; TestClient re-raises it in the test |
| `session_leak` | `test_no_connection_...` | the 404 request's session read chat 99 and was never closed, so it still holds a connection. A success-only leak test would miss it: the commit had already released that connection |
| `commit_after_yield` | `test_duplicate_...` | the endpoint returns 201 and the commit fails after the response. On the success path and the audit path, this mutant behaves correctly, which is why it ships so easily |
| `count_not_updated` | `test_send_saves_...` | only a check of `message_count` in the database sees it; the response looks fine |

**Why it works**

- **Read through a second session, after the request.** The app's session is gone when the request ends; `db` sees exactly what was committed. Because the fixtures use a file database, each session has its own connection, so uncommitted data can't leak into the check (the StaticPool trap from the last lesson).
- **`db.expire_all()`:** `db.get(Chat, 1)` would otherwise return the cached object from the previous snapshot with its old `message_count`. Expiring forces a fresh SELECT.
- **Compare a snapshot, not one number.** "Changes nothing" means *every* table the unit of work touches, plus the counter.

**Alternative:** check the audit outage at a lower level by unit-testing a `send_message(session, audit, ...)` service function with a raising fake. The HTTP-level test is still needed to prove the 503 mapping and that the dependency wiring uses the same session.
