---
{
  "id": "WEB.M05.L04",
  "title": "Testing failure paths: rollback and leaked connections",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["WEB.M05.L03", "WEB.M04"],
  "objectives": [
    "Inject a failure in the middle of a unit of work with dependency_overrides, and assert both the status code and that no rows were committed",
    "Read database state through a separate session after the request, and use expire_all() so cached objects don't hide changes",
    "Write a leak test with pool checkout/checkin events that includes error paths (404, 409), and explain why success-only leak tests miss bugs",
    "List the failure-path tests every database-backed endpoint needs"
  ],
  "why": "Transaction bugs and leaks are invisible on the happy path: every bug in this module returned the right status for a valid request. They show up only when something fails halfway, which in production means 3 a.m., under load, with partial data already written. A failure-path test makes the failure happen on purpose, in a test, and then looks at what's really in the database.",
  "applications": [
    "Proving an endpoint is atomic before a refactor or a library upgrade",
    "Reproducing a 'half-written data' incident as a failing test",
    "Catching connection leaks before they exhaust the production pool"
  ],
  "exercises": ["WEB.M05.L04.E1"],
  "sources": [
    {
      "title": "FastAPI Advanced: Testing Dependencies with Overrides",
      "url": "https://fastapi.tiangolo.com/advanced/testing-dependencies/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["app.dependency_overrides maps the original dependency to a replacement that FastAPI calls instead"]
    },
    {
      "title": "SQLAlchemy 2.1: Session Basics",
      "url": "https://docs.sqlalchemy.org/en/21/orm/session_basics.html",
      "version": "SQLAlchemy 2.1 docs; installed sqlalchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": [
        "Objects in a Session are expired when the transaction is closed out; the next access reloads them",
        "A Session used as a context manager is closed at the end of the with block"
      ]
    },
    {
      "title": "SQLAlchemy 2.1: Core Events (PoolEvents)",
      "url": "https://docs.sqlalchemy.org/en/21/core/events.html",
      "version": "SQLAlchemy 2.1 docs; installed sqlalchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["checkout is called when a connection is retrieved from the pool and checkin when it returns; pool events can be registered on an Engine"]
    },
    {
      "title": "pytest: How to use temporary directories and files in tests",
      "url": "https://docs.pytest.org/en/stable/how-to/tmp_path.html",
      "version": "pytest docs (stable); installed pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["tmp_path provides a temporary directory unique to each test function, as a pathlib.Path"]
    },
    {
      "title": "Starlette: Test Client",
      "url": "https://starlette.dev/testclient/",
      "version": "Starlette docs (current); installed starlette 1.10.0",
      "verified": "2026-11-12",
      "claims": ["raise_server_exceptions=False returns the 500 response instead of raising the exception in the test"]
    }
  ]
}
---
## 1. The status code is half the answer

For a write endpoint, every failure-path test has two asserts:

1. **The response:** the right status (404, 409, 503) and body.
2. **The database:** read through a *separate* session after the request, it contains exactly what it contained before.

The second half is the one people skip, and it's the one that catches transaction bugs. In the last two exercises, the early-commit bug and the commit-after-yield bug both gave reasonable-looking responses. Only a look at the tables showed the damage.

Use a **file database** (`tmp_path`) for these tests, so each session has its own connection. With StaticPool, the check could see uncommitted rows (lesson 3).

```quiz
{ "id": "q1", "type": "truefalse",
  "prompt": "If a failed request returns 409, the test has proven that nothing was written.", "answer": false,
  "explanation": "The status only says what the endpoint answered. An earlier commit in the same request, or a write outside the transaction, could still be in the database. Only reading the tables after the request shows it." }
```

## 2. Fault injection: make the middle of the unit fail

You can't make the database or a provider fail on demand, but you can replace a dependency that runs **between** the writes and the commit with one that raises. Here an invite writes two rows and calls a push provider before committing (the spec says: no member without a notification):

```python
@app.post("/chats/{chat_id}/invites/{user_id}", status_code=201)
def invite(chat_id: int, user_id: int,
           db: Annotated[Session, Depends(get_db)],
           push: Annotated[Push, Depends(get_push)]):
    db.add(Member(chat_id=chat_id, user_id=user_id))
    db.add(SystemEvent(text=f"user {user_id} joined"))
    db.flush()
    push.send(user_id, "you were added")   # inside the unit of work
    db.commit()
    return {"chat_id": chat_id, "user_id": user_id}
```

```python
def count(engine, model):
    with Session(engine) as check:
        return check.scalar(select(func.count()).select_from(model))


def test_push_outage_saves_nothing(engine):
    class PushDown:
        def send(self, user_id, text):
            raise ConnectionError("push provider timeout")

    app = create_app(engine)
    app.dependency_overrides[get_push] = PushDown
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/chats/1/invites/7")

    assert response.status_code == 500
    assert count(engine, Member) == 0
    assert count(engine, SystemEvent) == 0
```

```console
$ pytest -q
1 passed, 1 warning in 0.26s
```

- `app.dependency_overrides[get_push] = PushDown` passes the **class**. FastAPI calls the override, and calling a class creates an instance, so this works like `lambda: PushDown()`.
- The failure happens **after** `flush()`, so the rows really were sent to the database inside the transaction. That's the realistic case: the test proves the rollback, not just "nothing happened".
- `raise_server_exceptions=False` because nothing maps `ConnectionError` to a status here, so the client gets a 500. With an exception handler (like the exercise's 503), you don't need it.

Now break the app the way a refactor might: commit first, notify after.

```console
$ pytest -q        # with db.commit() moved above push.send(...)
>       assert count(engine, Member) == 0
E       assert 1 == 0
E        +  where 1 = count(Engine(sqlite:////tmp/pytest-of-root/pytest-154/test_push_outage_saves_nothing0/test.db), Member)
1 failed, 1 warning in 0.30s
```

**Design note:** whether a push belongs inside the transaction is a product decision. Many systems commit first and send notifications afterwards, from a queue, because a network call can't be rolled back and makes the transaction slow. The test doesn't decide the design, it pins down whichever one you chose.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "An endpoint writes rows A and B, then calls the audit dependency, then commits. Where should the injected failure happen to test atomicity best?",
  "options": ["In the audit call, after A and B were added and flushed", "In request validation, before the endpoint runs", "In the session dependency, before yield", "After the commit"], "answer": 0,
  "explanation": "A failure before any write proves nothing about rollback, because there was nothing to undo. A failure after the writes have reached the database, but before the commit, is the case that shows whether everything is undone." }
```

## 3. Reading the database: cached objects lie

A Session keeps the objects it loaded (the identity map). If your checking session already holds an object, another session's commit doesn't update it:

```python
checker = Session(engine)
chat = checker.get(Chat, 1)
print(chat.title)
with Session(engine) as app_session:      # the "request"
    app_session.get(Chat, 1).title = "new"
    app_session.commit()
print(checker.get(Chat, 1).title)
checker.expire_all()
print(chat.title)
```

```console
old
old
new
```

The second `get` didn't even query the database: it returned the cached object. `expire_all()` marks every cached object as stale, so the next attribute access reloads it. In a test that compares "before" and "after" through the same `db` session, call `db.expire_all()` before taking the "after" snapshot. Or use a new session for each check, like `count()` above.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import tempfile\nfrom sqlalchemy import String, create_engine\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Chat(Base):\n    __tablename__ = \"chats\"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    count: Mapped[int]\n\nengine = create_engine(f\"sqlite:///{tempfile.mkdtemp()}/t.db\")\nBase.metadata.create_all(engine)\nwith Session(engine) as s:\n    s.add(Chat(id=1, count=0))\n    s.commit()\n\nchecker = Session(engine)\nchat = checker.get(Chat, 1)\nwith Session(engine) as app_session:\n    app_session.get(Chat, 1).count += 1\n    app_session.commit()\nprint(chat.count, checker.get(Chat, 1).count)\nchecker.expire_all()\nprint(chat.count)",
  "answer": "0 0\n1",
  "explanation": "The checker cached chat 1 with count 0. get() returns the same cached object without a query, so both reads say 0. After expire_all(), the next access reloads it and sees the committed 1." }
```

## 4. Leak tests must include the error paths

Lesson 1 counted connections with pool events. Where you count matters. Here is a dependency with the "close after yield" bug from lesson 1's quiz, checked first after successful requests only and then after a 404:

```python
def get_db():
    db = SessionLocal()
    yield db
    db.close()          # skipped when the endpoint raises
```

```quiz
{ "id": "q4", "type": "output",
  "prompt": "The counter adds 1 on checkout and subtracts 1 on checkin. What does this print?",
  "code": "import gc\nimport tempfile\nfrom typing import Annotated\nfrom fastapi import Depends, FastAPI, HTTPException\nfrom fastapi.testclient import TestClient\nfrom sqlalchemy import String, create_engine, event\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Chat(Base):\n    __tablename__ = \"chats\"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    title: Mapped[str] = mapped_column(String(50))\n\ngc.disable()  # leaked sessions stay leaked\nengine = create_engine(f\"sqlite:///{tempfile.mkdtemp()}/t.db\")\nBase.metadata.create_all(engine)\nheld = {\"n\": 0}\nevent.listen(engine, \"checkout\", lambda *a: held.update(n=held[\"n\"] + 1))\nevent.listen(engine, \"checkin\", lambda *a: held.update(n=held[\"n\"] - 1))\nSessionLocal = sessionmaker(engine)\napp = FastAPI()\n\ndef get_db():\n    db = SessionLocal()\n    yield db\n    db.close()\n\n@app.post(\"/chats\", status_code=201)\ndef create_chat(title: str, db: Annotated[Session, Depends(get_db)]):\n    db.add(Chat(title=title))\n    db.commit()\n    return {\"ok\": True}\n\n@app.get(\"/chats/{chat_id}\")\ndef get_chat(chat_id: int, db: Annotated[Session, Depends(get_db)]):\n    chat = db.get(Chat, chat_id)\n    if chat is None:\n        raise HTTPException(status_code=404)\n    return {\"title\": chat.title}\n\nclient = TestClient(app)\nclient.post(\"/chats\", params={\"title\": \"ops\"})\nclient.get(\"/chats/1\")\nprint(\"after successes:\", held[\"n\"])\nclient.get(\"/chats/99\")\nprint(\"after a 404:\", held[\"n\"])",
  "answer": "after successes: 0\nafter a 404: 1",
  "explanation": "On success the generator resumes normally and close() runs. On the 404, HTTPException is thrown into the generator at yield, so the line after it never runs and the session keeps its connection. A leak test with only successful requests says 0 and passes." }
```

So a leak test sends **one request of each kind** (success, 404, 409, validation error), then asserts the count is back to zero. Each of those exits the dependency differently. Pause the garbage collector during the check (`gc.disable()` in the fixture, `gc.enable()` after `yield`), as the exercise's `connections` fixture does: otherwise it might reclaim the leaked session first and hide the leak.

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "A failure-path test does `before = snapshot(db)`, sends a failing request, then `assert snapshot(db) == before`, where snapshot reads `db.get(Chat, 1).message_count`. The test passes, but the endpoint really did commit a changed count. What's wrong with the test?",
  "options": ["db returns the cached Chat object from the first snapshot; it needs db.expire_all() (or a new session) before the second read", "The snapshot must be taken after the request", "message_count can't be read through a session", "The test should use StaticPool"], "answer": 0,
  "explanation": "The identity map gave back the object loaded by the first snapshot, with its old count, without querying. Expire first, or use a fresh session per check." }
```

## 5. Checklist: tests for a database-backed write endpoint

| Test | Asserts |
|---|---|
| Normal path | status and body, **plus every table the unit of work touches** |
| Each validation failure (422) and missing parent (404) | status, and no new rows |
| Each constraint conflict (409) | status, and the snapshot is unchanged |
| A dependency failing mid-unit (an override that raises) | status (500 or the mapped 503), and no new rows |
| Leaks | after one request of each kind, checked-out connections == 0 |
| Recovery | a valid request right after a failed one still works |

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Your team's Go service had a 'send message' RPC that wrote the message, bumped an unread counter and published a Kafka event. Pick the two failure-path tests you'd write first for a FastAPI version of it, and say exactly what each asserts.",
  "model": "1) Counter or event failure mid-unit: override the dependency that bumps the counter (or the publisher, if it's inside the transaction) with one that raises; assert the mapped status (500/503) and that the messages table and the counter are unchanged (read via a separate session with expire_all). 2) Duplicate client message id: send twice; assert 409 on the second and an unchanged snapshot (message count, counter). Plus a leak test covering success, 404 and 409.",
  "explanation": "Pick the failures that leave partial data in production: a step failing halfway, and a constraint conflict." }
```

## 6. Your turn

The send-message endpoint in the exercise is correct. Write the four failure-path tests and kill five mutants, including a leak that only shows on error paths and a commit that only fails on duplicates.

```exercise
WEB.M05.L04.E1
```
