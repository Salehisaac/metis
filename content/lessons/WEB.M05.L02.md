---
{
  "id": "WEB.M05.L02",
  "title": "One transaction per unit of work",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["WEB.M05.L01", "DB.M03"],
  "objectives": [
    "Identify the unit of work of an endpoint: the writes that must succeed or fail together",
    "Put exactly one commit per unit of work in the endpoint (or service), before the response, and explain why a commit after yield can tell the client 201 for unsaved data",
    "Use flush() to get database-generated ids and constraint errors without committing",
    "Turn an IntegrityError into a 409 with a rollback, and show with a test that a failed request leaves no rows behind"
  ],
  "why": "Your assessment answer was that a crash between two statements leaves both done. Transactions exist to make the opposite true: all of it or none of it. In a web app the question becomes where the transaction starts and ends. Put the commit in the wrong place and you get chats without members, 500s for a simple duplicate, or the worst case: the client is told 201 Created for a row that was never saved.",
  "applications": [
    "Creating an aggregate (chat + members + first message) in one request",
    "Admin actions that must change several tables together, such as ban user + revoke sessions + audit log",
    "Mapping unique-constraint violations to 409 Conflict"
  ],
  "exercises": ["WEB.M05.L02.E1"],
  "sources": [
    {
      "title": "FastAPI Advanced: Advanced Dependencies (dependencies with yield, technical details)",
      "url": "https://fastapi.tiangolo.com/advanced/advanced-dependencies/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": [
        "Since 0.118.0 the exit code after yield runs after the response is sent (default scope=\"request\")",
        "Depends(scope=\"function\") (added in 0.121.0) runs the exit code after the path operation function finishes, before the response is sent"
      ]
    },
    {
      "title": "FastAPI Tutorial: SQL (Relational) Databases",
      "url": "https://fastapi.tiangolo.com/tutorial/sql-databases/",
      "version": "FastAPI docs (current, examples use SQLModel); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["The path operation adds the object, commits, refreshes and returns it: the commit happens in the endpoint"]
    },
    {
      "title": "FastAPI Tutorial: Dependencies with yield",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["Exceptions raised in the path operation, including HTTPException, are passed to dependencies with yield; only one response is sent"]
    },
    {
      "title": "SQLAlchemy 2.1: Session Basics",
      "url": "https://docs.sqlalchemy.org/en/21/orm/session_basics.html",
      "version": "SQLAlchemy 2.1 docs; installed sqlalchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": [
        "Session.begin() as a context manager commits when the block ends normally and rolls back when it raises",
        "After a failed flush the transaction is rolled back and the application must call Session.rollback() explicitly",
        "Web applications: create a Session at the start of a request, commit for write requests, close it at the end",
        "All objects are expired when the transaction commits; expire_on_commit=False avoids reloading them"
      ]
    }
  ]
}
---
## 1. What is the unit of work?

In Go you write:

```go
tx, err := db.BeginTx(ctx, nil)
defer tx.Rollback()      // no-op after a successful Commit
// ... several Exec calls ...
return tx.Commit()
```

The transaction wraps **everything that must happen together**. That's the unit of work. For most endpoints it's simply "everything this request writes":

| Endpoint | Unit of work |
|---|---|
| `POST /chats` | the chat row, its member rows, the optional first message |
| `POST /chats/{id}/invites/{user}` | the member row and a "sara joined" system event |
| `POST /admin/users/{id}/ban` | the user's status, revoked sessions, an audit-log row |

The rule for this module: **one request, one unit of work, one commit, and the commit happens before the response is built.** If any step fails, nothing is committed and the client gets an error status.

SQLAlchemy starts the transaction for you on the first query (no `Begin` call). You decide where it **ends**: `commit()` makes it permanent, while `rollback()` or `close()` throws it away.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "An endpoint adds a chat, calls `commit()`, then adds two members and calls `commit()` again. The second member's user id doesn't exist, so the endpoint raises 404 before the second commit. What is in the database afterwards?",
  "options": ["The chat, with no members", "Nothing", "The chat and the first member", "The chat and both members"], "answer": 0,
  "explanation": "The first commit made the chat permanent. The member added afterwards was never committed, and closing the session rolls it back. Two commits means two units of work, which leaves a chat without members." }
```

## 2. The trap: committing after `yield`

Committing "at the end of the request" in the session dependency looks tidy: endpoints just `add()`, and the dependency commits. Run it with a duplicate:

```python
def get_db():
    with SessionLocal() as db:
        yield db
        db.commit()          # commit "at the end of the request"


@app.post("/chats", status_code=201)
def create_chat(title: str, db: Annotated[Session, Depends(get_db)]):
    db.add(Chat(title=title))
    return {"title": title}


client = TestClient(app, raise_server_exceptions=False)   # see what a real client sees
print(client.post("/chats", params={"title": "ops"}).status_code)
print(client.post("/chats", params={"title": "ops"}).status_code)   # duplicate!
with SessionLocal() as db:
    print("rows:", db.scalar(select(func.count()).select_from(Chat)))
```

```console
201
201
rows: 1
```

The second client was told **201 Created**, but its chat doesn't exist. As you saw in the last lesson, code after `yield` runs **after the response has been sent**. By the time the commit failed, the 201 was already on its way. The server logs an error that nobody connects to the "successful" request.

With the default `TestClient(app)` the test sees the `IntegrityError` raised, so a test does catch it. That's why the exercise's client uses `raise_server_exceptions=False`: it shows what a real client gets.

Real consequence in a messenger: the app shows "message sent", the user closes it, and the message is gone.

**The fix: commit inside the endpoint (or the service it calls)**, where a failure can still change the response. That's also where the FastAPI tutorial puts `session.commit()`. The dependency only opens and closes.

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "If `db.commit()` after `yield` in a session dependency fails, FastAPI changes the already-planned 201 response into a 500.", "answer": false,
  "explanation": "With the default scope, the exit code runs after the response has been sent, so it can't change the status anymore. Only one response is ever sent. Commit in the endpoint, before returning." }
```

## 3. `flush()`: talk to the database without committing

Often a later step needs an id the database generates (`chat.id` for the member rows). Committing early to get it is the bug from quiz 1. `flush()` sends the pending INSERTs **inside the open transaction**: ids are assigned and constraints are checked, but nothing is permanent yet.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "from sqlalchemy import String, create_engine, func, select\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Chat(Base):\n    __tablename__ = \"chats\"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    title: Mapped[str] = mapped_column(String(50))\n\nengine = create_engine(\"sqlite://\")\nBase.metadata.create_all(engine)\nwith Session(engine) as db:\n    chat = Chat(title=\"ops\")\n    db.add(chat)\n    print(chat.id)\n    db.flush()\n    print(chat.id)\n    db.rollback()\n    print(db.scalar(select(func.count()).select_from(Chat)))",
  "answer": "None\n1\n0",
  "explanation": "Before flush, the object only exists in Python, so it has no id. flush() runs the INSERT, and the database assigns id 1. rollback() undoes the uncommitted INSERT, so the table is empty again." }
```

Here is a complete unit of work: inviting a user adds a member row **and** a system event. Both commit together, and a duplicate invite (the composite primary key `(chat_id, user_id)` already exists) becomes a 409:

```python
@app.post("/chats/{chat_id}/invites/{user_id}", status_code=201)
def invite(chat_id: int, user_id: int, db: Annotated[Session, Depends(get_db)]):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    try:
        db.add(Member(chat_id=chat_id, user_id=user_id))
        db.add(SystemEvent(chat_id=chat_id, text=f"{user.username} joined"))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="already a member")
    return {"chat_id": chat_id, "user_id": user_id}
```

```console
$ # invite user 7, user 7 again, then user 8 (doesn't exist); then count members and events
201
409
404
1 1
```

- **One commit** for both rows. The second invite's system event was rolled back together with its member row, so there is still exactly one event.
- **`rollback()` before raising.** It puts the session back into a usable state. Here the dependency closes the session right after anyway, but in a longer endpoint, or a service that continues, it matters.
- **Why catch `IntegrityError` instead of checking first?** "SELECT, then INSERT if absent" has a race: two requests can both see "absent". The unique constraint is the real guard, and catching its error is the reliable check. (It's a race of the kind DB.M06 on concurrency covers.)
- **Catch narrowly.** `except Exception:` would turn real bugs into 409s.

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "A colleague's endpoint does `db.add(a)`, `db.add(b)`, `db.commit()` inside `try`, with `except IntegrityError: raise HTTPException(409)` and no rollback. The session comes from a per-request `with` dependency. Is the missing rollback a bug here?",
  "options": ["Not in practice: the dependency closes the session after the request, and closing rolls back", "Yes: a and b stay committed", "Yes: the next request on another session gets PendingRollbackError", "Yes: the 409 is never sent"], "answer": 0,
  "explanation": "With a per-request session, close() discards the failed transaction, and nobody else uses the session. The explicit rollback still makes sense if the endpoint keeps using the session after the error. With a shared session (lesson 1) the same code would poison every later request." }
```

## 4. Alternatives, and what to choose

- **`with db.begin():`** commits when the block ends normally and rolls back if it raises. It's neat in a service function that receives a fresh session. It raises an error if a transaction has already started in that session (for example, because an auth dependency already ran a query on the same session).
- **A transactional dependency, committed before the response.** `with factory.begin() as session: yield session`, declared with `Depends(get_session, scope="function")` (FastAPI 0.121+). The exit code then runs right after the endpoint returns, before the response, so a failed commit becomes a 500 instead of a false 201. You still catch `IntegrityError` in the endpoint if you want a 409.
- **`expire_on_commit=False`** on the sessionmaker. After a commit, SQLAlchemy expires loaded objects, so reading `chat.title` triggers a new SELECT. The SQLAlchemy docs suggest turning that off in web apps that read objects after committing, to build the response.

This module uses the explicit version: an endpoint (later a service) with one `commit()` in a `try`. It's the most visible: a reviewer sees exactly where the unit of work ends.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "This endpoint commits in the dependency after yield. The second POST is a duplicate. What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.testclient import TestClient\nfrom sqlalchemy import String, create_engine, func, select\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker\nfrom sqlalchemy.pool import StaticPool\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Chat(Base):\n    __tablename__ = \"chats\"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    title: Mapped[str] = mapped_column(String(50), unique=True)\n\nengine = create_engine(\"sqlite://\", connect_args={\"check_same_thread\": False}, poolclass=StaticPool)\nBase.metadata.create_all(engine)\nSessionLocal = sessionmaker(engine)\n\ndef get_db():\n    with SessionLocal() as db:\n        yield db\n        db.commit()\n\napp = FastAPI()\n\n@app.post(\"/chats\", status_code=201)\ndef create_chat(title: str, db: Annotated[Session, Depends(get_db)]):\n    db.add(Chat(title=title))\n    return {\"title\": title}\n\nclient = TestClient(app, raise_server_exceptions=False)\nprint(client.post(\"/chats\", params={\"title\": \"ops\"}).status_code)\nprint(client.post(\"/chats\", params={\"title\": \"ops\"}).status_code)\nwith SessionLocal() as db:\n    print(db.scalar(select(func.count()).select_from(Chat)))",
  "answer": "201\n201\n1",
  "explanation": "The duplicate's commit runs after the response was sent, so the client sees 201 although the row was never saved. One row exists: the first chat." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "In the admin panel you worked on, a ban did three writes: set the user's status to banned, delete their active sessions, insert an audit-log row. Describe how you would structure the FastAPI endpoint so the three writes are one unit of work, and which test proves it.",
  "model": "One session per request from a with-dependency that doesn't commit. In the endpoint (or a ban_user(session, ...) service): load the user (404 if missing), update the status, delete the sessions, add the audit row, then a single session.commit() in a try with except IntegrityError → rollback → 409/500 as appropriate. Test: make one step fail (for example, override a dependency so the audit writer raises, or violate a constraint), then check through a separate session that the user is not banned and the sessions still exist. That proves nothing was committed partially.",
  "explanation": "One commit after the last write, and a failure-path test that reads the database afterwards, is how you prove atomicity." }
```

## 5. Your turn

The exercise's `POST /chats` has all three bugs from this lesson: an early commit, an uncaught duplicate and a commit after `yield`. Make it one unit of work.

```exercise
WEB.M05.L02.E1
```
