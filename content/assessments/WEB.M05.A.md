---
{ "id": "WEB.M05.A", "module": "WEB.M05", "title": "WEB.M05 module assessment: database in FastAPI", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before WEB.M06.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "from sqlalchemy import String, create_engine, func, select\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column\n\nclass Base(DeclarativeBase):\n    pass\n\nclass User(Base):\n    __tablename__ = \"users\"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    name: Mapped[str] = mapped_column(String(30))\n\nengine = create_engine(\"sqlite://\")\nBase.metadata.create_all(engine)\nwith Session(engine) as s:\n    u = User(name=\"ali\")\n    s.add(u)\n    s.flush()\n    print(u.id)\n    s.add(User(name=\"sara\"))\n    s.commit()\n    s.add(User(name=\"reza\"))\n    s.flush()\n    s.rollback()\n    print(s.scalar(select(func.count()).select_from(User)))",
  "answer": "1\n2",
  "explanation": "flush() assigns ali's id (1) without committing. The commit makes ali and sara permanent. reza is flushed but rolled back, so 2 rows remain." }
```

```quiz
{ "id": "a2", "type": "choice", "label": "Debugging",
  "prompt": "After a few hours in production, every request fails with PendingRollbackError until the service restarts. The logs show one IntegrityError just before. What's the most likely cause?",
  "options": ["One Session object is shared by all requests, and nobody rolled it back after the failed flush", "The connection pool is too small", "The unique constraint is missing", "check_same_thread is True"], "answer": 0,
  "explanation": "A failed flush leaves the Session waiting for rollback(). If that session is shared, every later request inherits the broken state. A session per request (a yield dependency with `with`) makes each request start clean." }
```

```quiz
{ "id": "a3", "type": "truefalse",
  "prompt": "`def get_db(): with SessionLocal() as db: yield db; db.commit()` (commit after yield) guarantees the client gets an error status when the commit fails.", "answer": false,
  "explanation": "With FastAPI's default scope, code after yield runs after the response is sent. A failing commit there can't change the 201 the client already got. Commit inside the endpoint, before returning." }
```

```quiz
{ "id": "a4", "type": "choice",
  "prompt": "A test checks that a failed request left no rows behind. It uses `create_engine(\"sqlite://\", poolclass=StaticPool, connect_args={\"check_same_thread\": False})`, and the endpoint has a bug: it flushes but never commits. What does the test see?",
  "options": ["The uncommitted rows, because every session shares the one connection and its transaction", "An empty table, the correct result", "An OperationalError: no such table", "A ProgrammingError about threads"], "answer": 0,
  "explanation": "StaticPool hands all sessions the same connection, so a checker session sees what the app flushed in the open transaction. Use a tmp_path file database for commit and rollback tests." }
```

```quiz
{ "id": "a5", "type": "choice",
  "prompt": "Which set of requests should a connection-leak test send before asserting that no connection is checked out?",
  "options": ["A success, a 404, a 409 and a 422", "Ten successful requests", "One request with a very large body", "No requests: just check the pool at startup"], "answer": 0,
  "explanation": "Each kind of outcome leaves the session dependency differently. A close() that's skipped when an exception arrives only leaks on error paths, so success-only tests pass on broken code." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Design `POST /chats/{id}/messages` for a SQLAlchemy-backed FastAPI app: it saves the message, increments the chat's message_count, and rejects a duplicate client_id. Say where the session comes from, where the transaction starts and ends, how a duplicate becomes 409, and list the failure-path tests.",
  "model": "Session: a yield dependency, `with factory() as session: yield session`, one per request, never committing after yield. In the endpoint: 404 if the chat is missing; then in try: add the message, increment the counter, session.commit() once; except IntegrityError: session.rollback(), raise HTTPException(409). Tests on a tmp_path file database: normal (201, message row, count + 1, read via a separate session); duplicate (409, snapshot unchanged, with expire_all); a dependency failing mid-unit via dependency_overrides (500/503, nothing saved); unknown chat (404, nothing saved); a leak test covering success, 404 and 409 with pool events.",
  "explanation": "One session per request, one commit in the endpoint, and failure tests that read the tables afterwards." }
```
