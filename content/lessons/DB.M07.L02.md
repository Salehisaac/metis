---
{
  "id": "DB.M07.L02",
  "title": "The Session: unit of work and session.begin() transactions",
  "difficulty": "intermediate",
  "minutes": 80,
  "prerequisites": ["DB.M07.L01"],
  "objectives": [
    "Explain the Session as a unit of work with an identity map, and predict which SQL it sends and when",
    "Distinguish add, flush and commit, and explain expire_on_commit",
    "Frame a use case as one transaction with session.begin() / sessionmaker.begin() and rely on rollback on exception",
    "Apply 'one session per request or thread, never shared'"
  ],
  "why": "DB.M03 showed that a multi-step write must be one transaction or a crash leaves half of it behind. The Session is where SQLAlchemy decides when your INSERTs and UPDATEs actually reach the database and which transaction they're in. Most ORM bugs in production code (missing commits, half-saved data, stale objects) come from a fuzzy picture of exactly this.",
  "applications": [
    "One transaction per HTTP request or per use case in a FastAPI service",
    "Getting a generated id before inserting child rows",
    "Diagnosing 'my change wasn't saved' and 'I see old data after commit'"
  ],
  "exercises": ["DB.M07.L02.E1"],
  "sources": [
    {
      "title": "SQLAlchemy 2.1 Documentation: Session Basics",
      "url": "https://docs.sqlalchemy.org/en/21/orm/session_basics.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["The Session keeps an identity map: one object per primary key", "Changes are tracked using the unit of work pattern", "flush sends pending changes to the database; commit always flushes first", "with Session(engine) as session, session.begin(): commits at the end or rolls back on exception", "sessionmaker is a factory of Sessions with a fixed configuration", "After commit, all objects are expired and reload on next access", "A Session can't be shared among concurrent threads without careful synchronisation"]
    },
    {
      "title": "SQLAlchemy 2.1 Documentation: Transactions and Connection Management",
      "url": "https://docs.sqlalchemy.org/en/21/orm/session_transaction.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["Session.begin() / sessionmaker.begin() commit at the end of the block or roll back on an exception ('begin once')", "Without begin(), the Session autobegins a transaction and you commit as you go", "begin_nested() emits a SAVEPOINT"]
    },
    {
      "title": "SQLAlchemy 2.1 Documentation: ORM Quick Start",
      "url": "https://docs.sqlalchemy.org/en/21/orm/quickstart.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["Use the Session in context manager style", "session.scalars(select(...)) returns ORM objects; session.get(Model, pk) loads by primary key"]
    }
  ]
}
---
## 1. The Session: a workspace, not a connection

With `sqlite3` every `execute` went straight to the database. The ORM's `Session` sits in between. It keeps:

- an **identity map**: at most one Python object per row (per primary key) in this session;
- a **unit of work**: a list of new, changed and deleted objects it will turn into SQL later, in the right order.

The closest Go picture is a struct that wraps a `*sql.Tx` together with a `map[pk]*Row` cache and a list of pending changes, all flushed together. Watch what SQL goes out, and when (the models from L01, SQL logging switched on, timing lines trimmed):

```python
with Session(engine) as session:
    ali = User(username="ali")
    session.add(ali)
    print("after add:  ", ali.id)
    session.flush()
    print("after flush:", ali.id)
    same = session.get(User, ali.id)
    print("same object?", same is ali)
    session.commit()
    print("after commit, reading ali.username ...")
    print(ali.username)
```

```console
after add:   None
  SQL: BEGIN (implicit)
  SQL: INSERT INTO users (username, bio) VALUES (?, ?) RETURNING id, created_at
after flush: 1
same object? True
  SQL: COMMIT
after commit, reading ali.username ...
  SQL: BEGIN (implicit)
  SQL: SELECT users.id, users.username, users.bio, users.created_at
FROM users
WHERE users.id = ?
ali
  SQL: ROLLBACK
```

Line by line:

1. **`add()` sends nothing.** It puts the object in the unit of work. `ali.id` is still `None`.
2. **`flush()` sends the pending INSERT**, inside a transaction it started automatically (`BEGIN (implicit)`). SQLite ≥ 3.35 supports `RETURNING`, so the generated `id` and the database's `created_at` come back in the same statement.
3. **`session.get(User, 1)` sends no SQL**: the identity map already has that row, so you get *the same object* (`is`, not just `==`).
4. **`commit()` flushes anything left, then COMMITs.** It also **expires** every object, so the next attribute access reloads it in a new transaction: that's the SELECT before `ali`. You never act on stale data from before the commit.
5. Leaving the `with` block closes the session; the open read transaction is rolled back.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from sqlalchemy import create_engine\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Tag(Base):\n    __tablename__ = 'tags'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    name: Mapped[str]\n\nengine = create_engine('sqlite://')\nBase.metadata.create_all(engine)\nwith Session(engine) as s:\n    t = Tag(name='go')\n    s.add(t)\n    print(t.id)\n    s.flush()\n    print(t.id, s.get(Tag, 1) is t)",
  "answer": "None\n1 True",
  "explanation": "add() doesn't touch the database, so there's no id yet. flush() runs the INSERT and fills in id 1. get() finds the row in the identity map and returns the very same object." }
```

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "After `session.flush()`, the new rows are permanently saved and other connections can see them.", "answer": false,
  "explanation": "flush sends the SQL inside the session's open transaction. Until COMMIT, other connections can't see it, and a rollback undoes it." }
```

## 2. One use case, one transaction: begin()

Calling `commit()` yourself ("commit as you go") works, but it's easy to forget, or to commit halfway through a use case. The pattern for a use case is **begin once**:

```python
SessionLocal = sessionmaker(engine)          # a configured factory, created once

with SessionLocal.begin() as session:        # BEGIN ... COMMIT (or ROLLBACK on error)
    session.add_all([User(username="ali"), Chat(title="general")])
print("first block committed")

try:
    with SessionLocal.begin() as session:
        session.add(Chat(title="random"))
        session.add(User(username="ali"))       # duplicate username -> IntegrityError at flush
except IntegrityError as e:
    print("rolled back:", e.orig)
```

`with Session(engine) as session, session.begin():` is the same thing written without a factory. Output on this machine (with a final count, SQL logging off for it):

```console
  SQL: BEGIN (implicit)
  SQL: INSERT INTO chats (title) VALUES (?)
  SQL: INSERT INTO users (username, bio) VALUES (?, ?) RETURNING id, created_at
  SQL: COMMIT
first block committed
  SQL: BEGIN (implicit)
  SQL: INSERT INTO chats (title) VALUES (?)
  SQL: INSERT INTO users (username, bio) VALUES (?, ?) RETURNING id, created_at
  SQL: ROLLBACK
rolled back: UNIQUE constraint failed: users.username
chats: ['general']
users: 1
```

- The block **commits if it ends normally and rolls back if anything raises**: a database error or your own `raise LookupError(...)`. The "random" chat was inserted, then rolled back with the failing user. That's DB.M03's atomicity, with no `try/rollback` code to forget.
- The INSERTs were sent at the end of the block (at commit's flush), not when `add()` was called. The unit of work also chose the order itself.
- `e.orig` is the original `sqlite3` exception that SQLAlchemy wrapped.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "from sqlalchemy import create_engine, func, select\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Tag(Base):\n    __tablename__ = 'tags'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    name: Mapped[str] = mapped_column(unique=True)\n\nengine = create_engine('sqlite://')\nBase.metadata.create_all(engine)\nSession = sessionmaker(engine)\ntry:\n    with Session.begin() as s:\n        s.add(Tag(name='python'))\n        s.flush()\n        s.add(Tag(name='python'))\nexcept Exception as e:\n    print(type(e).__name__)\nwith Session() as s:\n    print(s.scalar(select(func.count()).select_from(Tag)))",
  "answer": "IntegrityError\n0",
  "explanation": "The first tag was flushed, but flushing isn't committing. The duplicate fails when the block flushes on exit, the whole transaction rolls back, and no tags remain." }
```

## 3. Needing an id before the commit

Child rows need the parent's id. Inside the block, `flush()` gives it to you without committing:

```python
with SessionLocal.begin() as session:
    chat = Chat(title="backend")
    session.add(chat)
    session.flush()                 # INSERT runs now; chat.id is set
    print("new chat id:", chat.id)  # still inside the transaction: a later error undoes it
```

```console
new chat id: 1
```

And a first query (L03 covers queries properly): `session.scalars(select(User).where(User.username == "ali")).one_or_none()` returns a `User` or `None`; `session.get(User, 5)` looks up a primary key (a tuple for a composite key, in column order).

## 4. Where sessions live

- **One session per request (or per thread, or per task), never shared.** The docs say a Session "cannot be shared among concurrent threads or asyncio tasks without careful synchronization": it's a mutable object with its own transaction. A global `session = Session(engine)` used by every request is a classic bug.
- **The engine and the sessionmaker are created once** per process and shared; they're designed for that.
- **Keep the transaction as short as the use case.** An open write transaction holds locks that make other writers wait (DB.M06 goes deeper): no HTTP calls inside `begin()`.
- `session.begin_nested()` gives you a SAVEPOINT for "try this part, undo just this part" inside a bigger transaction.

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "A FastAPI app creates `session = Session(engine)` once at import time and every request uses it. Under load you see odd errors and requests seeing each other's uncommitted data. What's the fix?",
  "options": ["Create a session per request (e.g. from a sessionmaker created once) and close it when the request ends", "Add a busy timeout", "Call session.commit() more often", "Use a separate engine per request"], "answer": 0,
  "explanation": "A Session is a single, stateful transaction workspace, not safe to share across concurrent requests. Share the engine and sessionmaker; give each request its own session." }
```

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "Inside `with SessionLocal.begin() as session:` your code raises `ValueError` after adding three objects. What reaches the database?",
  "options": ["Nothing: the transaction is rolled back and the ValueError propagates", "The three objects, because add() already saved them", "Only the objects added before the last flush", "The ValueError is swallowed and everything is committed"], "answer": 0,
  "explanation": "begin() commits only when the block finishes normally. Any exception rolls back everything, including flushed rows, and then propagates to the caller." }
```

## 5. Your turn

Write two use cases on the messenger models: `create_group` (a chat plus its members, all or nothing) and `add_member`. Each opens its own `begin()` block from the session factory it's given. The tests check that an unknown username leaves **no** chat behind, so validate inside the block and let the rollback do its job.

```exercise
DB.M07.L02.E1
```

```quiz
{ "id": "q6", "type": "explain", "label": "Explain",
  "prompt": "Explain the difference between add(), flush() and commit() to a Go developer, in three short lines.",
  "model": "add(): registers the object with the session's unit of work; no SQL yet. flush(): sends the pending INSERT/UPDATE/DELETE inside the current transaction (ids get filled in), still undoable. commit(): flushes, then COMMITs so the changes are permanent and visible to others, and expires loaded objects so they reload next time.",
  "explanation": "Like building up a batch, sending it on an open sql.Tx, and finally tx.Commit()." }
```
