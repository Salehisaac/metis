---
{
  "id": "DB.M06.L04",
  "title": "Optimistic concurrency with a version column",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["DB.M06.L03"],
  "objectives": [
    "Explain why a lock can't protect an edit that spans two HTTP requests",
    "Implement a compare-and-set UPDATE with a version column and detect conflicts with rowcount",
    "Decide between retrying automatically and reporting a conflict to the user (409)",
    "Choose between pessimistic locking (BEGIN IMMEDIATE, SELECT ... FOR UPDATE) and optimistic versioning for a given feature"
  ],
  "why": "L03's fixes work inside one request. Real edits span two: the client loads a form, a person types for a minute, the client saves. You suggested 409 Conflict in your assessment; this lesson is the database half of that instinct, and it's how ORMs, ETags and most collaborative apps avoid silently overwriting someone's work.",
  "applications": [
    "Editing a chat title, a profile or a document from two tabs or two devices",
    "REST APIs that answer 409 Conflict when a save is based on stale data",
    "SQLAlchemy's version_id_col and similar ORM features"
  ],
  "exercises": ["DB.M06.L04.E1"],
  "sources": [
    {
      "title": "SQLAlchemy 2.1 Documentation: Configuring a Version Counter",
      "url": "https://docs.sqlalchemy.org/en/21/orm/versioning.html",
      "version": "SQLAlchemy docs 2.1.8; behaviour verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["version_id_col adds a WHERE condition on the last known version to each UPDATE and DELETE", "If zero rows match, StaleDataError is raised", "The feature detects two concurrent transactions modifying the same row"]
    },
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (installed 3.12.3, SQLite 3.45.1)",
      "verified": "2026-11-12",
      "claims": ["Cursor.rowcount is the number of modified rows for UPDATE"]
    },
    {
      "title": "PostgreSQL 18 Documentation: 13.3 Explicit Locking",
      "url": "https://www.postgresql.org/docs/current/explicit-locking.html",
      "version": "PostgreSQL 18 (docs 18.7); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["SELECT ... FOR UPDATE locks rows against other writers and lockers until the transaction ends", "Deadlocks are detected and one transaction is aborted"]
    }
  ]
}
---
## 1. An edit that spans two requests

Alice and Bob both open the "rename chat" form:

1. Request 1 (Alice): `GET /chats/1` → title "general".
2. Request 1 (Bob): same.
3. Alice types "General chat" and saves: `PUT /chats/1`.
4. Bob, a minute later, types "Off-topic" and saves.

Bob's save overwrites Alice's, and he never saw her change. It's L03's lost update, but the "read" and the "write" are **separate HTTP requests minutes apart**.

You can't fix this with L03's tools. `title = title + ...` doesn't apply, because the new value is whatever a human typed. And holding a lock (BEGIN IMMEDIATE, or `SELECT ... FOR UPDATE`) between two requests would mean every other writer waits while Alice thinks, and a lock held by a closed browser tab would never be released.

```quiz
{ "id": "q1", "type": "truefalse",
  "prompt": "A good fix for the rename-chat problem is to run BEGIN IMMEDIATE when the form is loaded and COMMIT when it's saved.", "answer": false,
  "explanation": "That holds the database's write lock (or a row lock, in PostgreSQL) for as long as a person takes to type, across two requests, and forever if they close the tab. Locks belong inside one short request." }
```

## 2. The version column: compare-and-set

Instead of locking, **detect** the conflict at save time. Add `version INTEGER NOT NULL DEFAULT 1`. Every read returns the version along with the data; every save says "only if the version is still the one I read", and bumps it:

```python
# Both open the "rename chat" form: read the title AND its version.
a_title, a_version = alice.execute("SELECT title, version FROM chats WHERE id = 1").fetchone()
b_title, b_version = bob.execute("SELECT title, version FROM chats WHERE id = 1").fetchone()
print("alice sees", (a_title, a_version), "| bob sees", (b_title, b_version))

RENAME = "UPDATE chats SET title = ?, version = version + 1 WHERE id = ? AND version = ?"
print("alice saves:", alice.execute(RENAME, ("General chat", 1, a_version)).rowcount, "row")
print("bob saves:  ", bob.execute(RENAME, ("Off-topic", 1, b_version)).rowcount, "rows")
print(setup.execute("SELECT title, version FROM chats WHERE id = 1").fetchone())
```

```console
alice sees ('general', 1) | bob sees ('general', 1)
alice saves: 1 row
bob saves:   0 rows
('General chat', 2)
```

The check (`version = ?`) and the write happen **in one statement**, so they're atomic (the L03 rule again). Alice's save moved the version to 2, so Bob's `WHERE version = 1` matches nothing. `rowcount == 0` is the conflict signal. Nothing was overwritten.

It's Go's `atomic.CompareAndSwapInt64(&v, old, new)`, with a row instead of an integer. It's called **optimistic** because it assumes conflicts are rare, takes no lock in advance, and pays only when one actually happens.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:', isolation_level=None)\nconn.execute('CREATE TABLE docs (id INTEGER PRIMARY KEY, body TEXT, version INTEGER)')\nconn.execute(\"INSERT INTO docs VALUES (1, 'v1 text', 1)\")\nsave = 'UPDATE docs SET body = ?, version = version + 1 WHERE id = ? AND version = ?'\nprint(conn.execute(save, ('a', 1, 1)).rowcount, conn.execute(save, ('b', 1, 1)).rowcount, conn.execute(save, ('c', 1, 2)).rowcount)\nprint(conn.execute('SELECT body, version FROM docs').fetchone())",
  "answer": "1 0 1\n('c', 3)",
  "explanation": "'a' matches version 1 and bumps it to 2. 'b' still claims version 1, so it matches nothing. 'c' claims version 2 (a fresh read) and wins, making it 3." }
```

**Common mistakes**

- Checking the version with a SELECT and then running a plain UPDATE. That's the L03 race again; the check must be in the UPDATE's WHERE clause.
- Forgetting `version = version + 1`. Then every save keeps version 1 and nothing is ever detected.
- Treating `rowcount == 0` as "conflict" without considering "the row was deleted". If you need to tell them apart, check existence **after** the failed UPDATE, on the rare failure path.

## 3. On conflict: retry or report?

Two very different situations:

- **The change is computed from the current state** (add a tag, increment, append to a list): re-read, re-apply, try the compare-and-set again, in a loop with a small limit. Nobody's intent is lost.
- **A person chose the new value** based on what they saw: **don't** retry silently. That would just overwrite the other save in two steps. Report it. An HTTP API answers `409 Conflict`; the client reloads, shows the current value and lets the person decide.

```quiz
{ "id": "q3", "type": "choice", "label": "Application",
  "prompt": "A profile save fails the version check (0 rows updated). The new bio was typed by the user. What should the API do?",
  "options": ["Return 409 Conflict so the client can show the latest bio and let the user decide", "Re-read the version and save the user's bio again automatically", "Return 200 and ignore it", "Retry until it succeeds"], "answer": 0,
  "explanation": "Auto-retrying a human's edit just overwrites the other person's save one step later. Detecting the conflict is pointless unless someone gets to resolve it." }
```

## 4. Pessimistic or optimistic?

| | Pessimistic: lock first | Optimistic: version check |
|---|---|---|
| Tools | `BEGIN IMMEDIATE` (SQLite), `SELECT ... FOR UPDATE` (PostgreSQL/MySQL, not run here) | `version` column, `WHERE version = ?`, rowcount |
| Holds a lock | for the whole transaction | never across requests |
| Conflict cost | others **wait** | the loser gets an **error** and redoes work |
| Good for | short, high-contention updates inside one request (balances, counters, job queues) | edits that span requests, rare conflicts, a human in the loop |
| Risks | waiting, deadlocks (PostgreSQL aborts one transaction) | retry loops under heavy contention |

And remember the cheapest option from L03: if the change fits in one `UPDATE ... SET x = x + 1`, you need neither.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "A 'reserve a seat' endpoint gets hundreds of requests per second for the same concert at sale start. Which approach fits best?",
  "options": ["One atomic UPDATE ... SET seats_left = seats_left - 1 WHERE id = ? AND seats_left > 0", "Optimistic versioning with automatic retries", "Read seats_left, then UPDATE with the computed value", "Ask users to retry manually"], "answer": 0,
  "explanation": "Under heavy contention, optimistic retries mostly fail and retry again. The change fits in one conditional UPDATE, which serialises cleanly with no retries and no lost updates." }
```

## 5. The same idea in SQLAlchemy

SQLAlchemy builds this in: map a version column and the ORM adds `AND version = ?` to its UPDATEs. Two sessions load the same chat, both change it, both commit (SQLAlchemy 2.1.6 on this machine):

```python
class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    version: Mapped[int] = mapped_column(nullable=False)
    __mapper_args__ = {"version_id_col": version}

alice, bob = Session(engine), Session(engine)
a_chat, b_chat = alice.get(Chat, 1), bob.get(Chat, 1)
print("both loaded version", a_chat.version, b_chat.version)
a_chat.title = "General chat"
alice.commit()
b_chat.title = "Off-topic"
try:
    bob.commit()
except StaleDataError as e:
    print("StaleDataError:", e)
```

```console
both loaded version 1 1
StaleDataError: UPDATE statement on table 'chats' expected to update 1 row(s); 0 were matched.
```

Same mechanism, same signal ("0 were matched"), raised as an exception. In an API you'd translate `StaleDataError` into a 409. (This only protects a version the client actually sent back: across HTTP requests the client must include the version it read, and your handler must use it.)

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "A team added a version column, but conflicts are never detected. Their save is `UPDATE chats SET title = ?, version = version + 1 WHERE id = ?` after `SELECT version` showed the expected value. What's wrong?",
  "options": ["The version check isn't in the UPDATE's WHERE clause, so the check and the write aren't atomic", "The version should be a timestamp", "They need SERIALIZABLE isolation for versions to work", "version + 1 should be computed in Python"], "answer": 0,
  "explanation": "Between the SELECT and the UPDATE another save can happen, and the UPDATE matches the row anyway. The compare must be part of the write: WHERE id = ? AND version = ?." }
```

## 6. Your turn

Implement profile edits with a version column: `get_profile()` returns the bio and its version, and `update_bio()` saves only if nobody saved in between. The tests use two connections (Alice and Bob), check that a missing user isn't reported as a conflict, and trace your SQL to make sure the check is in the UPDATE itself.

```exercise
DB.M06.L04.E1
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Your Go messenger lets admins edit a group's description. Describe, end to end (client, API, database), how you'd stop two admins from silently overwriting each other.",
  "model": "Add a version column to the group. GET returns the description and version (for example in the body or an ETag). The client sends the version back with the PUT. The handler runs UPDATE groups SET description = ?, version = version + 1 WHERE id = ? AND version = ?. If rowcount is 1, return the new version; if 0, check whether the group exists (404) or answer 409 Conflict with the current data, and the client shows it to the admin to merge or retry.",
  "explanation": "Optimistic concurrency spans the whole round trip: the version has to travel to the client and back." }
```
