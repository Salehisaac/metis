---
{
  "id": "WEB.M05.L01",
  "title": "A session per request: the yield dependency",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["WEB.M04", "DB.M07", "PY.M07"],
  "objectives": [
    "Explain the different lifetimes of an engine (one per app), a sessionmaker (one per app) and a Session (one per request)",
    "Explain why one Session shared by all requests turns one failed request into an outage (PendingRollbackError)",
    "Write a yield dependency that opens a session, yields it, and always closes it, and predict when its exit code runs",
    "Detect a leaked connection with pool.status() or pool checkout/checkin events"
  ],
  "why": "In Go you share one *sql.DB (a pool) and open a short *sql.Tx per unit of work; nobody shares a Tx across goroutines. SQLAlchemy has the same split under different names, and getting it wrong in FastAPI fails in two nasty ways: one bad request poisons every later request, or connections leak until the pool is empty and the API hangs. Both look fine in a quick manual test and break under real traffic.",
  "applications": [
    "The get_session dependency that every database endpoint in a FastAPI project uses",
    "Diagnosing 'QueuePool limit ... reached' timeouts in production",
    "Reviewing a pull request that stores a session on a global or on app.state"
  ],
  "exercises": ["WEB.M05.L01.E1"],
  "sources": [
    {
      "title": "FastAPI Tutorial: SQL (Relational) Databases",
      "url": "https://fastapi.tiangolo.com/tutorial/sql-databases/",
      "version": "FastAPI docs (current, examples use SQLModel); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": [
        "A dependency with yield provides a new Session for each request, which ensures a single session per request",
        "check_same_thread=False lets FastAPI use the same SQLite database from different threads, because one request can use more than one thread"
      ]
    },
    {
      "title": "FastAPI Tutorial: Dependencies with yield",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": [
        "Code up to and including yield runs before the response is created; the yielded value is injected",
        "Normally the exit code of a dependency with yield runs after the response is sent",
        "finally makes sure exit steps run whether or not there was an exception"
      ]
    },
    {
      "title": "SQLAlchemy 2.1: Session Basics",
      "url": "https://docs.sqlalchemy.org/en/21/orm/session_basics.html",
      "version": "SQLAlchemy 2.1 docs; installed sqlalchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": [
        "A Session used in a with block is closed at the end of the block",
        "Keep the lifecycle of the session separate and external from functions that access data",
        "Web applications: create a Session at the start of a request and close it at the end",
        "sessionmaker is a factory for Session objects with a fixed configuration, created once at module/global scope",
        "After a failed flush the transaction is rolled back, but the application must call Session.rollback() before using the session again"
      ]
    },
    {
      "title": "SQLAlchemy 2.1: Connection Pooling",
      "url": "https://docs.sqlalchemy.org/en/21/core/pooling.html",
      "version": "SQLAlchemy 2.1 docs; installed sqlalchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": [
        "QueuePool defaults: pool_size 5, max_overflow 10, timeout 30 seconds",
        "Closing a pooled connection returns it to the pool, which rolls it back on return by default",
        "Pool.status() returns a brief description of the pool's state"
      ]
    },
    {
      "title": "FastAPI Advanced: Advanced Dependencies (dependencies with yield, technical details)",
      "url": "https://fastapi.tiangolo.com/advanced/advanced-dependencies/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": [
        "Before 0.118.0 (since 0.106.0) the exit code ran after the path operation returned but before the response was sent; 0.118.0 reverted to running it after the response is sent",
        "0.121.0 added Depends(scope=\"function\"), whose exit code runs before the response is sent; scope=\"request\" is the default"
      ]
    },
    {
      "title": "SQLAlchemy 2.1: SQLite dialect",
      "url": "https://docs.sqlalchemy.org/en/21/dialects/sqlite.html",
      "version": "SQLAlchemy 2.1 docs; installed sqlalchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["File databases use QueuePool, and check_same_thread is set to False by default unless overridden"]
    },
    {
      "title": "SQLAlchemy 2.1: Core Events (PoolEvents)",
      "url": "https://docs.sqlalchemy.org/en/21/core/events.html",
      "version": "SQLAlchemy 2.1 docs; installed sqlalchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["PoolEvents.checkout is called when a connection is retrieved from the pool, checkin when it returns; listeners can be registered on an Engine"]
    }
  ]
}
---
## 1. Three objects, three lifetimes

You met these in DB.M07. In a web app, what matters is **how long each one lives**:

| SQLAlchemy | Lives | Go equivalent |
|---|---|---|
| `Engine` (with its connection pool) | the whole process, created once | `*sql.DB` |
| `sessionmaker(engine)` | the whole process: a factory with fixed settings | a constructor function |
| `Session` | **one request** (one unit of work) | roughly a `*sql.Tx` plus an object cache |

A Session isn't a connection. It borrows a connection from the pool when it first needs one (the first query starts a transaction automatically), and gives it back when the transaction ends or the session is closed. It also tracks every object you loaded or added. That's why it must not be shared: it holds **one transaction's state**.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Which object should be created exactly once when the app starts, and shared by all requests?",
  "options": ["The Engine", "The Session", "A Session per worker thread", "A new Engine per request"], "answer": 0,
  "explanation": "The engine owns the connection pool, so it's long-lived and shared, like *sql.DB in Go. Sessions are cheap and short-lived: one per request. A new engine per request would create a new pool every time." }
```

## 2. The shared session: one bad request takes everyone down

It's tempting to open one session at startup and reuse it, like a global DB handle. Here's what happens when one request violates a unique constraint (pure SQLAlchemy, no FastAPI, so you can see it clearly):

```python
engine = create_engine("sqlite://")
Base.metadata.create_all(engine)
shared = Session(engine)  # one session for "every request"

shared.add(Chat(title="ops"))
shared.commit()                      # request 1: fine

shared.add(Chat(title="ops"))        # request 2: duplicate title
try:
    shared.commit()
except IntegrityError as exc:
    print("request 2:", type(exc).__name__)

try:
    shared.scalars(select(Chat)).all()   # request 3: an innocent read
except Exception as exc:
    print("request 3:", type(exc).__name__)
```

```console
request 2: IntegrityError
request 3: PendingRollbackError
```

After a failed flush, SQLAlchemy rolls back the database transaction, but the Session refuses further work until someone calls `session.rollback()`. Request 2's handler didn't. Request 3 belongs to a different user who did nothing wrong, and it fails anyway, and so will every request after it until the process restarts.

With threads it gets worse. FastAPI runs `def` endpoints in a thread pool, so two requests could use the same Session at the same time, mixing their objects and transactions.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "from sqlalchemy import String, create_engine, select\nfrom sqlalchemy.exc import IntegrityError\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Chat(Base):\n    __tablename__ = \"chats\"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    title: Mapped[str] = mapped_column(String(50), unique=True)\n\nengine = create_engine(\"sqlite://\")\nBase.metadata.create_all(engine)\nshared = Session(engine)\nshared.add(Chat(title=\"ops\"))\nshared.commit()\nshared.add(Chat(title=\"ops\"))\ntry:\n    shared.commit()\nexcept IntegrityError:\n    shared.rollback()\nprint(len(shared.scalars(select(Chat)).all()))",
  "answer": "1",
  "explanation": "This time the handler calls rollback(), so the session is usable again: the duplicate is discarded and the read returns the one committed chat. Remembering to roll back in every handler is fragile, though. A fresh session per request makes the problem impossible." }
```

## 3. The yield dependency

A dependency with `yield` is a generator: FastAPI runs it up to `yield`, injects the yielded value, runs the endpoint, and resumes the generator afterwards. You built the same shape in PY.M07 with context managers. Here it is with prints, so you can see the order:

```python
engine = create_engine("sqlite:///./chat.db")
SessionLocal = sessionmaker(engine)
app = FastAPI()


def get_db():
    print("1. open session")
    with SessionLocal() as session:
        yield session
        print("3. after yield: request is done")
    print("4. session closed")


@app.get("/health/db")
def db_health(db: Annotated[Session, Depends(get_db)]):
    print("2. endpoint runs")
    return {"db": db.scalar(text("SELECT 1"))}
```

```console
1. open session
2. endpoint runs
3. after yield: request is done
4. session closed
{'db': 1}
```

- **The `with` block is what makes it safe.** If the endpoint raises, FastAPI throws the exception into the generator at `yield`, the `with` block exits, and the session is closed anyway. A `session.close()` written as a plain line after `yield` would be skipped when an exception arrives. (`try: yield session` / `finally: session.close()` is the equivalent without `with`.)
- **Closing rolls back** whatever wasn't committed and returns the connection to the pool.
- **When does step 3 run?** Since FastAPI 0.118, the code after `yield` runs **after the response has been sent** (the default `scope="request"`). For closing a session that's fine. In the next lesson you'll see why it's the wrong place for `commit()`.

The FastAPI docs keep `SessionLocal` at module level and write `SessionDep = Annotated[Session, Depends(get_db)]` so endpoints just say `session: SessionDep`. In this module the exercises put the session factory on `app.state` inside `create_app(engine)`, so a test can build an app on a test engine (lesson 3).

**SQLite and threads:** a request can touch more than one thread (FastAPI runs `def` endpoints and dependencies in a thread pool), which plain `sqlite3` connections refuse by default. The FastAPI docs pass `connect_args={"check_same_thread": False}`. For file databases, SQLAlchemy 2.1 already sets it to `False` for you; for in-memory test databases you'll need it explicitly in lesson 3.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.testclient import TestClient\nfrom sqlalchemy import create_engine, text\nfrom sqlalchemy.orm import Session, sessionmaker\n\nSessionLocal = sessionmaker(create_engine(\"sqlite://\"))\napp = FastAPI()\n\ndef get_db():\n    print(\"open\")\n    with SessionLocal() as session:\n        yield session\n    print(\"closed\")\n\n@app.get(\"/ping\")\ndef ping(db: Annotated[Session, Depends(get_db)]):\n    print(\"endpoint\")\n    return db.scalar(text(\"SELECT 1\"))\n\nr = TestClient(app).get(\"/ping\")\nprint(r.json())",
  "answer": "open\nendpoint\nclosed\n1",
  "explanation": "Code before yield, then the endpoint, then the exit code. TestClient returns only after the whole request has finished, exit code included, so 'closed' appears before the test prints the body." }
```

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "In FastAPI 0.162 with default settings, the code after `yield` in a dependency runs before the response is sent to the client.", "answer": false,
  "explanation": "By default (scope=\"request\") the exit code runs after the response is sent. FastAPI 0.106 to 0.117 ran it before; 0.118 reverted that. Depends(..., scope=\"function\") (0.121+) runs it right after the endpoint returns, before the response." }
```

## 4. Leaked sessions: the pool runs dry

A session that is never closed keeps its connection while it has a transaction open. The pool hands out a limited number of connections (by default `pool_size=5` plus `max_overflow=10`), and the next request waits up to `timeout` (30 s by default) for one, then fails. Here's a leaky dependency with a deliberately tiny pool, so it breaks quickly:

```python
engine = create_engine(f"sqlite:///{tempfile.mkdtemp()}/chat.db", pool_size=2, max_overflow=0, pool_timeout=1)
SessionLocal = sessionmaker(engine)
app = FastAPI()


def get_db_leaky():
    session = SessionLocal()
    yield session          # never closed


@app.get("/health/db")
def db_health(db: Annotated[Session, Depends(get_db_leaky)]):
    return {"db": db.scalar(text("SELECT 1"))}


client = TestClient(app)
for i in range(3):
    try:
        print(i, client.get("/health/db").status_code, engine.pool.status())
    except Exception as exc:
        print(i, type(exc).__name__, str(exc).split(",")[0])
```

```console
0 200 Pool size: 2  Connections in pool: 0 Current Overflow: -1 Current Checked out connections: 1
1 200 Pool size: 2  Connections in pool: 0 Current Overflow: 0 Current Checked out connections: 2
2 TimeoutError QueuePool limit of size 2 overflow 0 reached
```

Each request did a read, which started a transaction, and nobody ended it. Two requests later the pool is empty, and the third request waits a second and dies. (Nothing references these sessions any more, so Python's garbage collector may eventually reclaim one and return its connection, and SQLAlchemy may warn when that happens. That's luck, not a fix: under load the pool runs dry first. The exercise fixtures pause the garbage collector during leak checks so a leak always shows.) In production with the default pool (5 + 10 connections), leaked sessions pile up until requests start hanging and then fail, often only under load. Your Go equivalent is forgetting `rows.Close()` or `tx.Rollback()`.

**How tests detect it:** `engine.pool.status()` is fine for a quick look. In a test, count with pool events, which are part of SQLAlchemy's public API:

```python
@event.listens_for(engine, "checkout")
def on_checkout(*args):
    counts["out"] += 1


@event.listens_for(engine, "checkin")
def on_checkin(*args):
    counts["in"] += 1
```

After the requests have finished, `counts["out"] - counts["in"]` must be 0. The exercise's `connections` fixture does exactly this.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print? (It takes about a second.)",
  "code": "import gc\nimport tempfile\nfrom typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.testclient import TestClient\nfrom sqlalchemy import create_engine, text\nfrom sqlalchemy.orm import Session, sessionmaker\n\ngc.disable()  # keep leaked sessions leaked (see the note above)\nengine = create_engine(f\"sqlite:///{tempfile.mkdtemp()}/t.db\", pool_size=2, max_overflow=0, pool_timeout=1)\nSessionLocal = sessionmaker(engine)\napp = FastAPI()\n\ndef get_db():\n    session = SessionLocal()\n    yield session\n\n@app.get(\"/ping\")\ndef ping(db: Annotated[Session, Depends(get_db)]):\n    return db.scalar(text(\"SELECT 1\"))\n\nclient = TestClient(app)\nfor i in range(3):\n    try:\n        print(client.get(\"/ping\").status_code)\n    except Exception as exc:\n        print(type(exc).__name__)",
  "answer": "200\n200\nTimeoutError",
  "explanation": "The session is never closed, so each request keeps a connection. The pool has 2 and no overflow, so the third request waits pool_timeout (1 s) and gets TimeoutError. Wrapping the yield in `with SessionLocal() as session:` fixes it." }
```

```quiz
{ "id": "q6", "type": "choice", "label": "Debugging",
  "prompt": "A dependency is `session = SessionLocal()`, `yield session`, `session.close()`. Under load the pool still runs dry, and it happens on requests that ended with an HTTPException. Why?",
  "options": ["The exception is thrown into the generator at yield, so the close() line never runs", "HTTPException closes the engine", "close() must come before yield", "Sessions can't be closed inside a dependency"], "answer": 0,
  "explanation": "When the endpoint raises, FastAPI throws the exception into the dependency at the yield, and the plain line after it is skipped. Use `with SessionLocal() as session: yield session`, or try/finally, so closing happens on every path." }
```

## 5. Your turn

The exercise is a refactor: `create_app` shares one session across all requests. The tests reproduce both failures from this lesson: the poisoned session and the held connection.

```exercise
WEB.M05.L01.E1
```
