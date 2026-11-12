---
{
  "id": "WEB.M05.L03",
  "title": "A test database: SQLite in memory or in a temp file",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["WEB.M05.L02", "WEB.M04"],
  "objectives": [
    "Choose between an in-memory SQLite database, a temporary SQLite file and the production database engine for a given test, and name what each can't show",
    "Configure an in-memory SQLite engine that works with FastAPI's worker threads, and diagnose the 'no such table' and 'same thread' errors",
    "Write engine, session and client fixtures that give each test a fresh database and clean up after yield",
    "Explain why StaticPool can hide a missing commit, and use a tmp_path file database for commit and rollback tests"
  ],
  "why": "In the assessment you picked 'a test database or fakes' for testing code that talks to a database: the right instinct. This lesson turns it into working fixtures. Integration tests against a real SQL engine catch what fakes can't: wrong queries, missing commits, constraint violations. Each test needs its own clean database, or you're back to tests that pass alone and fail together.",
  "applications": [
    "The conftest.py of every FastAPI + SQLAlchemy project",
    "Running the full API test suite in CI without a database server",
    "Reproducing a constraint or transaction bug in a test before fixing it"
  ],
  "exercises": ["WEB.M05.L03.E1"],
  "sources": [
    {
      "title": "SQLAlchemy 2.1: SQLite dialect (threading/pooling, memory databases)",
      "url": "https://docs.sqlalchemy.org/en/21/dialects/sqlite.html",
      "version": "SQLAlchemy 2.1 docs; installed sqlalchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": [
        "sqlite:// (nothing after the slashes) is an in-memory database; a :memory: database exists only within a single DBAPI connection",
        "A :memory: database uses SingletonThreadPool by default (one connection per thread); file databases use QueuePool",
        "StaticPool makes every checkout return the same connection; it doesn't support concurrency and suits fully serialized access such as single-threaded test suites",
        "Sessions that share that one connection share its single SQLite transaction state"
      ]
    },
    {
      "title": "SQLAlchemy 2.1: Connection Pooling",
      "url": "https://docs.sqlalchemy.org/en/21/core/pooling.html",
      "version": "SQLAlchemy 2.1 docs; installed sqlalchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["StaticPool is a pool of exactly one connection, used for all requests"]
    },
    {
      "title": "FastAPI Tutorial: SQL (Relational) Databases",
      "url": "https://fastapi.tiangolo.com/tutorial/sql-databases/",
      "version": "FastAPI docs (current, examples use SQLModel); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": [
        "check_same_thread=False is needed because one request can use more than one thread",
        "For production you'd probably use a migration script instead of creating tables at startup"
      ]
    },
    {
      "title": "pytest: How to use fixtures",
      "url": "https://docs.pytest.org/en/stable/how-to/fixtures.html",
      "version": "pytest docs (stable); installed pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["Teardown code goes after the yield; function scope is the default"]
    },
    {
      "title": "FastAPI Advanced: Testing Dependencies with Overrides",
      "url": "https://fastapi.tiangolo.com/advanced/testing-dependencies/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["Any dependency, such as a session dependency, can be replaced for tests through app.dependency_overrides"]
    }
  ]
}
---
## 1. Which database do tests use?

| Option | Speed | Shows | Can't show |
|---|---|---|---|
| A fake repository (a dict) | fastest | your endpoint logic | SQL mistakes, constraints, commits |
| **SQLite in memory** | very fast, nothing on disk | queries, constraints, unique violations | commit/rollback bugs (with StaticPool, section 4); PostgreSQL-only behaviour |
| **SQLite in a temp file** | fast | all of the above, plus commits, rollbacks and pool leaks | PostgreSQL-only behaviour |
| The production engine (PostgreSQL in Docker) | slowest, needs a server | everything, including types, locking and JSONB | nothing, if set up correctly |

This module uses SQLite, which is all this machine has (no Docker or PostgreSQL here). SQLite differs from PostgreSQL in types, some constraints and concurrency, so a project usually adds a smaller suite against the real engine in CI. That comes in DB.M08 and the OPS course.

Whatever you choose, **each test gets its own fresh database**. That's the database version of WEB.M04's "fresh app per test".

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A test must prove that a failed request leaves no rows behind (nothing was committed). Which database fits best?",
  "options": ["SQLite in a temporary file", "A dict-based fake repository", "SQLite in memory with StaticPool", "The production database"], "answer": 0,
  "explanation": "A fake has no transactions at all. In memory with StaticPool, every session shares one connection, so a check can see uncommitted rows (section 4). A temp file gives each session its own connection, like a real server, and never touches production." }
```

## 2. In-memory SQLite and threads: two errors to recognise

An in-memory database exists **inside one connection**: another connection sees a different, empty database. FastAPI runs `def` endpoints in worker threads, and SQLAlchemy's default pool for `sqlite://` gives each thread its own connection. So the tables you created in the test thread are invisible to the endpoint:

```quiz
{ "id": "q2", "type": "output", "label": "Debugging",
  "prompt": "The tables are created right after the engine. What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.testclient import TestClient\nfrom sqlalchemy import String, create_engine, select\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Chat(Base):\n    __tablename__ = \"chats\"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    title: Mapped[str] = mapped_column(String(50))\n\nengine = create_engine(\"sqlite://\")\nBase.metadata.create_all(engine)\nSessionLocal = sessionmaker(engine)\napp = FastAPI()\n\ndef get_db():\n    with SessionLocal() as db:\n        yield db\n\n@app.get(\"/chats\")\ndef list_chats(db: Annotated[Session, Depends(get_db)]):\n    return [c.title for c in db.scalars(select(Chat))]\n\ntry:\n    print(TestClient(app).get(\"/chats\").json())\nexcept Exception as exc:\n    print(type(exc).__name__, \"no such table\" in str(exc))",
  "answer": "OperationalError True",
  "explanation": "create_all ran on the test thread's connection. The endpoint ran in a worker thread, got its own connection, and with it a brand-new empty in-memory database: no such table: chats." }
```

The fix is `poolclass=StaticPool`: one connection, handed to everyone. That brings the second error. Python's `sqlite3` refuses to use a connection from a thread other than the one that created it:

```console
sqlalchemy.exc.ProgrammingError: (sqlite3.ProgrammingError) SQLite objects created in a thread
can only be used in that same thread. The object was created in thread id 135883998879872 and
this is thread id 135883951261376.
```

So the in-memory recipe needs **both** settings:

```python
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
```

`check_same_thread=False` is safe here only because a test suite talks to the database one request at a time. The SQLAlchemy docs say StaticPool doesn't support concurrency.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "With `poolclass=StaticPool`, each Session gets its own database connection.", "answer": false,
  "explanation": "StaticPool is a pool of exactly one connection, used for all requests. That's what makes the in-memory database visible everywhere, and it's also its weakness (section 4)." }
```

## 3. Fixtures: engine, session, client

A test database needs three fixtures. They build on WEB.M04.L02:

1. **`engine`:** a new engine per test, then `Base.metadata.create_all(engine)` to create the tables. After `yield`, call `engine.dispose()`. In production, Alembic migrations create the tables (DB.M07). Running the migrations in tests as well also tests the migrations, but takes longer.
2. **`db` (a Session):** for the test's own Arrange and Assert steps. You insert rows directly instead of through other endpoints, so a bug in `POST /users` can't break every chat test. Then you check what was really saved. `with Session(engine) as ...:` and `yield` inside the block.
3. **`client`:** a TestClient for an app built **on the test engine**. With a factory like `create_app(engine)` you just pass it in. With the FastAPI docs' module-level `get_session`, you set `app.dependency_overrides[get_session]` to a function that yields a session on the test engine instead.

```python
def test_list_shows_committed_chats(client, db):
    db.add_all([Chat(title="ops"), Chat(title="random")])   # Arrange, straight into the DB
    db.commit()

    response = client.get("/chats")                          # Act, through the API

    assert response.json() == ["ops", "random"]
```

```console
$ pytest -q        # with a small GET /chats app and engine/db/client fixtures as described above
1 passed, 1 warning in 0.04s
```

**Common mistakes**

- **An engine fixture with `scope="session"` and no cleanup.** Data from one test leaks into the next. If you widen the scope for speed, you need a per-test cleanup step, which is more code that can be wrong.
- **Forgetting `db.commit()` in Arrange.** With a temp file database, the app's session can't see your uncommitted rows. (With StaticPool it can, which hides the mistake until you switch.)
- **Importing the production `app` in conftest.py.** Every request then goes to the production URL. In the exercise that URL is unreachable on purpose, like a CI runner without network access to the database.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "Why insert test data through the `db` session instead of calling `POST /users` and `POST /chats` in Arrange?",
  "options": ["So a bug in another endpoint can't make this test fail, and Arrange stays fast and explicit", "Because TestClient can't send two requests in one test", "Because the API can't write to an in-memory database", "Because sessions are faster than SQL"], "answer": 0,
  "explanation": "Arranging through other endpoints couples tests together: one broken POST makes dozens of unrelated tests red. Direct inserts set up exactly the state the test needs. Use the API for the Act step only." }
```

## 4. StaticPool can hide a missing commit

All sessions on a StaticPool engine share one connection, and therefore its transaction. A test that checks "was it saved?" through a second session sees the app's **uncommitted** work:

```quiz
{ "id": "q5", "type": "output",
  "prompt": "The app session flushes but never commits. What does the checker session count?",
  "code": "from sqlalchemy import String, create_engine, func, select\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column\nfrom sqlalchemy.pool import StaticPool\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Chat(Base):\n    __tablename__ = \"chats\"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    title: Mapped[str] = mapped_column(String(50))\n\nengine = create_engine(\"sqlite://\", poolclass=StaticPool)\nBase.metadata.create_all(engine)\napp_session = Session(engine)\napp_session.add(Chat(title=\"ops\"))\napp_session.flush()\nwith Session(engine) as checker:\n    print(checker.scalar(select(func.count()).select_from(Chat)))",
  "answer": "1",
  "explanation": "The checker uses the same single connection, inside the same open transaction, so it sees the flushed but uncommitted row. A test would wrongly conclude the data was saved." }
```

Run the same script with a temporary file instead (`create_engine(f"sqlite:///{tempfile.mkdtemp()}/t.db")`) and it prints `0`: each session gets its own connection from a QueuePool, exactly like a real database server. So:

- **In memory + StaticPool:** fine for most endpoint tests (status codes, bodies, queries).
- **Temp file:** for tests about commits, rollbacks and leaked connections. pytest's built-in `tmp_path` fixture gives each test its own new temporary directory:

```python
@pytest.fixture
def file_engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()
```

The previous lesson's exercise used exactly this fixture. Now you know why: an in-memory database would have let the "201 but not saved" bug pass.

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "A teammate's conftest.py uses one module-level in-memory engine with StaticPool for all tests, and a test checks 'after a failed request, the messages table is empty'. Name two separate ways this setup can give wrong results, and what you'd change.",
  "model": "1) Shared engine: every test uses the same in-memory database, so rows from earlier tests leak into later ones (order-dependent results). Fix: function-scoped engine fixture with create_all, disposed after yield. 2) StaticPool shares one connection and its transaction, so the check can see uncommitted rows: a test of 'nothing was saved' or 'it was committed' can pass on broken code. Fix: a tmp_path file database for commit and rollback tests.",
  "explanation": "Fresh database per test, and a real per-session connection when the test is about transactions." }
```

## 5. Your turn

The exercise's tests are written. The fixtures are not, and the app they import points at a production database path that doesn't exist here. Write the in-memory test database fixtures.

```exercise
WEB.M05.L03.E1
```
