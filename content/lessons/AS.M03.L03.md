---
{
  "id": "AS.M03.L03",
  "title": "Async database access: a connection per request with aiosqlite (and async SQLAlchemy)",
  "difficulty": "intermediate",
  "minutes": 100,
  "prerequisites": ["AS.M03.L02"],
  "objectives": [
    "Query SQLite from async def endpoints with aiosqlite without blocking the event loop",
    "Write a request-scoped async DB dependency that commits on success, rolls back and re-raises on error, and always closes, and state why each rule exists",
    "Explain what Depends(..., scope=\"function\") changes about when the commit runs, using a measured example",
    "Test an async DB app with a file database in tmp_path, and explain why ':memory:' fails with one connection per request",
    "Use async SQLAlchemy in FastAPI (create_async_engine, async_sessionmaker.begin() as the session dependency, selectinload) and state its rules: one session per task, no implicit lazy loading"
  ],
  "why": "AS.M03.L01 showed that a sync DB call inside async def blocks every request. To keep endpoints async you need an async driver, and the unit-of-work rules from WEB.M05 (one transaction per request, no leaked sessions) have to be expressed with await. Getting the dependency right is most of the job.",
  "applications": [
    "Async FastAPI services on SQLite (aiosqlite) or PostgreSQL (asyncpg via async SQLAlchemy)",
    "Request-scoped sessions that commit or roll back as one unit of work",
    "Integration tests against a throwaway database file"
  ],
  "exercises": ["AS.M03.L03.E1"],
  "sources": [
    {
      "title": "aiosqlite documentation",
      "url": "https://aiosqlite.omnilib.dev/en/stable/",
      "version": "aiosqlite stable docs (installed aiosqlite 0.22.1)",
      "verified": "2026-11-12",
      "claims": ["aiosqlite provides an async interface to sqlite databases mirroring the sqlite3 module", "It uses a single, shared thread per connection that executes all actions from a request queue, so queries don't block the event loop", "Usage: async with aiosqlite.connect(...), await db.execute(...), await db.commit(), await cursor.fetchall(), db.row_factory = aiosqlite.Row"]
    },
    {
      "title": "FastAPI docs: Dependencies with yield",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/",
      "version": "FastAPI docs (page states no version; installed fastapi 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Code after yield normally runs after the response is sent", "Depends(scope=\"function\") ends the dependency after the path operation function but before the response is sent; scope=\"request\" (the default for yield dependencies) ends after the response is sent", "If you catch an exception in a dependency with yield you should re-raise it, otherwise the server has no log of the error"]
    },
    {
      "title": "SQLAlchemy 2.1: Asynchronous I/O (asyncio)",
      "url": "https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html",
      "version": "SQLAlchemy docs 2.1.8; installed sqlalchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["The asyncio extension needs greenlet, which is not installed by default as of 2.1; install sqlalchemy[asyncio] (greenlet 3.5.6 is installed here)", "create_async_engine creates an AsyncEngine; example URLs include sqlite+aiosqlite:// and postgresql+asyncpg://", "async_sessionmaker(engine, expire_on_commit=False) is recommended so attributes stay readable after commit", "AsyncSession is not safe for use in multiple concurrent tasks; use a separate AsyncSession per task", "Avoid lazy loading with AsyncSession: use eager loading such as selectinload, lazy='raise', or AsyncAttrs.awaitable_attrs", "Use AsyncConnection.run_sync() for MetaData.create_all", "Call await engine.dispose() when the engine goes out of scope"]
    },
    {
      "title": "SQLAlchemy 2.1: Transactions and Connection Management (Session.begin)",
      "url": "https://docs.sqlalchemy.org/en/21/orm/session_transaction.html",
      "version": "SQLAlchemy docs 2.1.8; installed sqlalchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["At the end of a session.begin() block pending objects are flushed and the transaction is committed", "If an exception is raised within the block, the transaction is rolled back", "sessionmaker.begin() creates the session and begins the transaction in one step"]
    },
    {
      "title": "FastAPI docs: Async Tests",
      "url": "https://fastapi.tiangolo.com/advanced/async-tests/",
      "version": "FastAPI docs (page states no version; installed fastapi 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["In async tests you can await other async functions, e.g. to check the database after a request", "AsyncClient won't trigger lifespan events"]
    }
  ]
}
---
## 1. Why an async driver

WEB.M05 gave you a request-scoped DB session and one transaction per unit of work. If that session is sync (`sqlite3`, SQLAlchemy's `Session`), every query blocks its thread, so per AS.M03.L01 those endpoints must be plain `def`. To keep endpoints `async def`, the driver itself must be awaitable.

For SQLite that's **aiosqlite**. Its docs explain how it works: each connection gets **one dedicated thread** that runs the real `sqlite3` calls from a request queue, so your `await db.execute(...)` suspends the coroutine while that thread does the work, and the loop stays free. (So "async SQLite" is still a thread underneath, one per connection.)

The API mirrors `sqlite3`, with `await` in front: `await db.execute(...)`, `await cursor.fetchone()`, `await db.commit()`.

## 2. aiosqlite basics, and the unit-of-work rules

A plain script first, run on this machine:

```python
import asyncio, threading
import aiosqlite

async def main():
    print("threads before:", threading.active_count())
    async with aiosqlite.connect("shop.db") as db:
        print("threads while connected:", threading.active_count())
        await db.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)")
        cursor = await db.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("kettle", 30))
        print("new id:", cursor.lastrowid)
        await db.commit()
        cursor = await db.execute("SELECT name, price FROM products WHERE id = ?", (cursor.lastrowid,))
        print(await cursor.fetchone())
    print("threads after close:", threading.active_count())

asyncio.run(main())
```

```console
threads before: 1
threads while connected: 2
new id: 1
('kettle', 30)
threads after close: 1
```

The extra thread is the connection's worker thread from the aiosqlite docs. It goes away when the connection is closed, which is one more reason never to leak connections.

In a FastAPI app you don't open connections in each endpoint. You write a **dependency with `yield`** (PY.M07.L04, WEB.M05) that gives each request its own connection and turns the request into one unit of work. The rules are the same as in WEB.M05, now with `await`:

| When | What the dependency must do | Why |
|---|---|---|
| The endpoint returned normally | commit | the request's writes become one transaction |
| The endpoint raised (even `HTTPException`) | roll back, then **re-raise** | FastAPI throws the endpoint's exception in at the `yield`; the FastAPI docs say to re-raise it, or the server has no log of the error |
| Always, including cancellation | close the connection | `CancelledError` isn't an `Exception` (AS.M02.L03), so only a `finally` (or `async with`) is sure to run |
| Every request | a new connection | concurrent requests must never share one transaction |

You'll write exactly this dependency for aiosqlite in the exercise. Section 5 shows the same rules expressed in SQLAlchemy's own idiom, where a context manager does the commit and rollback for you.

```quiz
{ "id": "q1", "type": "choice", "label": "Debugging",
  "prompt": "A dependency does `try: yield db` / `finally: await db.commit(); await db.close()`. What goes wrong?",
  "options": ["Nothing; finally is the right place for both", "Requests that fail halfway still commit their partial writes", "The connection is never closed", "The commit runs before the endpoint"], "answer": 1,
  "explanation": "finally runs on errors too, so a request that raised after two of three inserts commits those two. Commit only on the success path; roll back on errors; close in finally." }
```

## 3. When does the commit run? `scope="function"`

The FastAPI docs: normally the code after `yield` runs **after the response is sent**. That's the default `scope="request"` for dependencies with `yield`. With `Depends(..., scope="function")`, the dependency ends after the endpoint function and **before** the response is sent.

That matters for a commit. Measured on this machine with a real server (uvicorn 0.54.0) and a dependency whose exit code takes 0.3 s:

```python
async def slow_exit():
    try:
        yield "dep"
    finally:
        await asyncio.sleep(0.3)          # stands in for a slow commit

@app.get("/request-scope")
async def a(d: Annotated[str, Depends(slow_exit)]):
    return {"ok": True}

@app.get("/function-scope")
async def b(d: Annotated[str, Depends(slow_exit, scope="function")]):
    return {"ok": True}
```

```console
$ python -m uvicorn f4:app --port 8791     # then timed httpx.get() against each path
request-scope 200 0.02s
function-scope 200 0.32s
```

With the default scope, the client had its `200` after 0.02 s, *before* the exit code ran. If that exit code is a commit and the commit fails (a constraint, a lock timeout), the client has already been told "success". `scope="function"` makes the client wait for the commit, so a failed commit becomes an error response. That's why the SQLAlchemy example in section 5 and the exercise use it.

(Through `AsyncClient` + `ASGITransport`, both scopes took 0.30 s on this machine: the transport waits for the whole app call to finish. Your tests can't see this difference, which is exactly why it's worth knowing.)

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "With the default scope for a `yield` dependency that commits after `yield`, what can a client observe that it can't with `scope=\"function\"`?",
  "options": ["A 201 response for data whose commit later fails", "A 500 response for every request", "Requests that never get a response", "Two commits for one request"], "answer": 0,
  "explanation": "By default the exit code (the commit) runs after the response has been sent, so a commit failure can't change the response anymore. scope=\"function\" runs it before the response." }
```

## 4. Testing it: a real file, not `:memory:`

The test setup from L02 applies: AnyIO tests and `AsyncClient`. Two DB-specific points.

**Use a temporary file.** With one connection per request, `":memory:"` doesn't work: every connection to `":memory:"` is its own new, empty database.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import asyncio, aiosqlite\n\nasync def main():\n    async with aiosqlite.connect(\":memory:\") as first:\n        await first.execute(\"CREATE TABLE t (x INTEGER)\")\n    async with aiosqlite.connect(\":memory:\") as second:\n        cur = await second.execute(\"SELECT name FROM sqlite_master\")\n        print(await cur.fetchall())\n\nasyncio.run(main())",
  "answer": "[]",
  "explanation": "The second connection opens a brand-new in-memory database, which has no tables. Point tests at a file under pytest's tmp_path instead." }
```

So in tests: a file under pytest's `tmp_path`, the app's DB path pointed at it (`monkeypatch.setattr(module, "DB_PATH", ...)` or `app.dependency_overrides`), and the schema created in the test or a fixture. Not in lifespan: `AsyncClient` doesn't run lifespan events (L02).

**Check the database with a separate connection.** After a request, open your own connection and `SELECT`. That proves the data was **committed**: another connection can't see uncommitted writes.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import asyncio, os, tempfile, aiosqlite\n\nasync def main():\n    path = os.path.join(tempfile.mkdtemp(), \"demo.db\")\n    async with aiosqlite.connect(path) as writer:\n        await writer.execute(\"CREATE TABLE t (x INTEGER)\")\n        await writer.commit()\n        await writer.execute(\"INSERT INTO t VALUES (1)\")   # not committed yet\n        async with aiosqlite.connect(path) as reader:\n            cur = await reader.execute(\"SELECT COUNT(*) FROM t\")\n            print((await cur.fetchone())[0])\n\nasyncio.run(main())",
  "answer": "0",
  "explanation": "The insert is part of the writer's open transaction. Until it commits, other connections still see the table as empty." }
```

## 5. The same rules with async SQLAlchemy

With SQLAlchemy you get the ORM on top, and the session gives you a shorter way to express the unit of work. Run on this machine (sqlalchemy 2.1.6, greenlet 3.5.6, aiosqlite 0.22.1):

```python
import asyncio
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    category: Mapped[Category] = relationship(back_populates="products")


engine = create_async_engine("sqlite+aiosqlite:///catalog.db")
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    # new session + transaction: commits if the block ends normally,
    # rolls back if an exception comes in at the yield, closes the session either way
    async with async_session.begin() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]
app = FastAPI()


@app.post("/categories", status_code=201)
async def create_category(name: str, products: list[str], session: SessionDep):
    category = Category(name=name)
    session.add(category)
    await session.flush()                      # INSERT sent now, so category.id is known
    for product_name in products:
        if not product_name.strip():           # fails AFTER the category row was inserted
            raise HTTPException(status_code=422, detail="blank product name")
        session.add(Product(name=product_name, category_id=category.id))
    return {"id": category.id, "name": name}


@app.get("/categories/{category_id}")
async def read_category(category_id: int, session: SessionDep):
    stmt = select(Category).where(Category.id == category_id).options(selectinload(Category.products))
    category = (await session.execute(stmt)).scalars().first()
    if category is None:
        raise HTTPException(status_code=404, detail="category not found")
    return {"name": category.name, "products": [p.name for p in category.products]}


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/categories", params={"name": "tea"}, json=["green", "black"])
        print(r.status_code, r.json())
        print((await client.get("/categories/1")).json())
        r = await client.post("/categories", params={"name": "mugs"}, json=["big", " "])
        print(r.status_code, r.json())
        print((await client.get("/categories/2")).status_code)

    async with async_session() as session:     # what happens without selectinload?
        category = (await session.execute(select(Category))).scalars().first()
        try:
            print(category.products)
        except Exception as e:
            print(type(e).__name__, "|", str(e).split(";")[0])
    await engine.dispose()


asyncio.run(main())
```

```console
201 {'id': 1, 'name': 'tea'}
{'name': 'tea', 'products': ['green', 'black']}
422 {'detail': 'blank product name'}
404
StatementError | (sqlalchemy.exc.MissingGreenlet) greenlet_spawn has not been called
sys:1: RuntimeWarning: coroutine 'Connection.cursor' was never awaited
```

What to read from the output:

- **The rollback is real.** The `mugs` request inserted its category (the `flush` sent the INSERT), then hit the blank product name and raised. `GET /categories/2` is a 404: the exception reached `get_session` at the `yield`, and `async_session.begin()` rolled the whole transaction back. The SQLAlchemy docs on `session.begin()`: at the end of the block pending objects are flushed and the transaction is committed; if an exception was raised in the block, it's rolled back. `async_sessionmaker.begin()` creates the session and begins in one step. Compare this with the table in section 2: the same four rules, but the context manager does commit, rollback, re-raise and close for you.
- **`selectinload` is not optional.** The last part loads a category *without* it and touches `category.products`. A lazy load would need database I/O inside a plain attribute access, where nothing can `await` it, so SQLAlchemy raises (`MissingGreenlet`, wrapped in a `StatementError`) instead of blocking. The SQLAlchemy docs tell you to avoid lazy loading with `AsyncSession`: load what you need up front with `selectinload(...)`, or use `lazy="raise"` or `AsyncAttrs.awaitable_attrs`. (The RuntimeWarning on the last line is a side effect of that failed lazy load.)
- **DDL goes through `run_sync`**: `create_all` has no awaitable version, so `await conn.run_sync(Base.metadata.create_all)` runs it. `await engine.dispose()` closes the pool at the end, as the docs advise.
- **`expire_on_commit=False`** keeps objects readable after the commit without another query, as the docs recommend.

The rule this example doesn't show, but which matters most with `gather` (AS.M02): **one `AsyncSession` per task.** The SQLAlchemy docs say an `AsyncSession` is not safe for use in multiple concurrent tasks. A per-request dependency gives you one per request; running several queries concurrently on that one session doesn't.

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "To speed up an endpoint you run three queries concurrently with `asyncio.gather`, all on the request's single `AsyncSession`. This is safe.", "answer": false,
  "explanation": "The SQLAlchemy docs: AsyncSession is not safe for use in multiple concurrent tasks; use a separate session per task. Sequential awaits on one session are fine." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Your team is moving a FastAPI service from sync SQLAlchemy (def endpoints) to async SQLAlchemy (async def endpoints). List three things that must change or be checked, and why.",
  "model": "1) The driver and engine: an async dialect (e.g. postgresql+asyncpg, sqlite+aiosqlite), create_async_engine, async_sessionmaker, and greenlet installed (sqlalchemy[asyncio]). 2) The session dependency: async generator, one AsyncSession per request and never shared across concurrent tasks, commit on success and rollback on error (async_sessionmaker.begin() does both), scope=\"function\" so the commit happens before the response. 3) Every remaining blocking call inside the now-async endpoints (sync clients, file I/O) must be awaited or moved to to_thread, and relationships must be loaded eagerly (selectinload), because lazy loads fail with AsyncSession. Tests switch to AnyIO + AsyncClient with a file DB.",
  "explanation": "Driver, session lifecycle, and hidden blocking or lazy I/O." }
```

## 6. Your turn

The exercise is a notes API on aiosqlite. Its connection dependency never commits, never rolls back and never closes. Fix it so every request is one unit of work, and write the read endpoint. The tests check the database with their own connection, and count every connection opened and closed.

```exercise
AS.M03.L03.E1
```
