---
{
  "id": "DB.M08.L02",
  "title": "RETURNING and ON CONFLICT: upserts without races",
  "difficulty": "intermediate",
  "minutes": 80,
  "prerequisites": ["DB.M08.L01"],
  "objectives": [
    "Use INSERT/UPDATE/DELETE ... RETURNING to get generated or changed values in the same statement, and know its limits",
    "Replace check-then-insert with INSERT ... ON CONFLICT DO NOTHING / DO UPDATE, using excluded and the stored row",
    "Write a conditional upsert (DO UPDATE ... WHERE, or max()/GREATEST) that never moves a value backwards",
    "Build the same upsert with SQLAlchemy's SQLite and PostgreSQL insert() and read the PostgreSQL SQL it compiles to"
  ],
  "why": "'Insert if missing, otherwise update' appears everywhere: read markers, contacts, settings, idempotent API calls. Written as SELECT-then-INSERT it races (DB.M06). PostgreSQL's ON CONFLICT, which SQLite copied, does it in one atomic statement, and RETURNING tells you what happened without a second query.",
  "applications": [
    "Idempotent endpoints: 'join chat', 'add contact', 'like' that can be retried safely",
    "Read markers and last-seen timestamps that arrive out of order",
    "Getting a new row's id and defaults without a second query"
  ],
  "exercises": ["DB.M08.L02.E1"],
  "sources": [
    {
      "title": "The RETURNING Clause (SQLite)",
      "url": "https://www.sqlite.org/lang_returning.html",
      "version": "SQLite docs, page updated 2025-05-31; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["RETURNING works on top-level DELETE, INSERT and UPDATE since SQLite 3.35.0, modelled after PostgreSQL", "For INSERT/UPDATE it returns values after the change; for DELETE, before", "RETURNING on an UPSERT reports inserted and updated rows", "Rows come back in arbitrary order", "It can't be used as a subquery and only returns directly modified rows"]
    },
    {
      "title": "UPSERT (SQLite)",
      "url": "https://www.sqlite.org/lang_upsert.html",
      "version": "SQLite docs, page updated 2024-04-11; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["ON CONFLICT turns an INSERT that would violate a uniqueness constraint into an UPDATE or a no-op", "The conflict target must be a UNIQUE/PRIMARY KEY constraint or unique index", "excluded.col is the value that would have been inserted; bare col is the stored value", "A WHERE on DO UPDATE can turn it into a no-op", "Syntax follows PostgreSQL; added in 3.24.0"]
    },
    {
      "title": "PostgreSQL 18 Documentation: INSERT",
      "url": "https://www.postgresql.org/docs/current/sql-insert.html",
      "version": "PostgreSQL 18 (docs 18.7); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["ON CONFLICT DO NOTHING / DO UPDATE with the special excluded table", "DO UPDATE requires a conflict target", "ON CONFLICT DO UPDATE guarantees an atomic INSERT or UPDATE outcome, even under high concurrency", "RETURNING returns rows actually inserted or updated"]
    },
    {
      "title": "PostgreSQL 18 Documentation: 6.4 Returning Data from Modified Rows",
      "url": "https://www.postgresql.org/docs/current/dml-returning.html",
      "version": "PostgreSQL 18 (docs 18.7); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["INSERT, UPDATE, DELETE and MERGE support RETURNING, which avoids an extra query", "INSERT ... RETURNING id returns a generated id"]
    },
    {
      "title": "PostgreSQL 18 Documentation: 9.18 Conditional Expressions (GREATEST)",
      "url": "https://www.postgresql.org/docs/current/functions-conditional.html",
      "version": "PostgreSQL 18 (docs 18.7); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["GREATEST selects the largest value from a list of expressions; NULLs are ignored"]
    },
    {
      "title": "SQLAlchemy 2.1 Documentation: SQLite and PostgreSQL dialects (INSERT…ON CONFLICT)",
      "url": "https://docs.sqlalchemy.org/en/21/dialects/sqlite.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["sqlalchemy.dialects.sqlite.insert provides on_conflict_do_update() and on_conflict_do_nothing()", "set_ takes a dict; stmt.excluded refers to the proposed row"]
    }
  ]
}
---
## 1. RETURNING: what did that statement just do?

In DB.M04 you read `cursor.lastrowid` after an INSERT and ran a second SELECT for anything else. `RETURNING` hands back columns of the rows a statement changed, **in the same statement**. PostgreSQL has had it for years; SQLite added it in 3.35.0. Check before relying on it:

```python
print("SQLite", sqlite3.sqlite_version)
conn = sqlite3.connect(":memory:", isolation_level=None)
conn.execute("""CREATE TABLE messages (
    id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, body TEXT NOT NULL,
    likes INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

row = conn.execute(
    "INSERT INTO messages (chat_id, body) VALUES (?, ?) RETURNING id, likes, created_at", (1, "hi")
).fetchone()
print("inserted:", row)

row = conn.execute("UPDATE messages SET likes = likes + 1 WHERE id = ? RETURNING likes", (1,)).fetchone()
print("likes now:", row)

print("no match:", conn.execute("UPDATE messages SET likes = likes + 1 WHERE id = ? RETURNING likes", (99,)).fetchone())

rows = conn.execute("DELETE FROM messages WHERE chat_id = ? RETURNING id, body", (1,)).fetchall()
print("deleted:", rows)
```

```console
SQLite 3.45.1
inserted: (1, 0, '2026-11-12 16:46:36')
likes now: (1,)
no match: None
deleted: [(1, 'hi')]
```

- The INSERT returned the generated id **and** the database defaults (`likes`, `created_at`). SQLAlchemy uses exactly this on SQLite: you saw `INSERT ... RETURNING id, created_at` in DB.M07.
- `UPDATE ... SET likes = likes + 1 RETURNING likes` is DB.M06's atomic increment that also tells you the new value. No match returns no row.
- For DELETE, RETURNING shows the rows as they were before deletion.

Limits from the SQLite docs: rows come back in **arbitrary order** (sort them yourself), only rows the statement changed directly are returned (not cascaded deletes), and a statement with RETURNING can't be used as a subquery. PostgreSQL also supports RETURNING on `MERGE`.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:', isolation_level=None)\nconn.execute('CREATE TABLE tags (name TEXT PRIMARY KEY, uses INTEGER NOT NULL)')\nsql = 'INSERT INTO tags VALUES (?, 1) ON CONFLICT (name) DO UPDATE SET uses = uses + 1 RETURNING uses'\nfor name in ['go', 'py', 'go', 'go']:\n    print(name, conn.execute(sql, (name,)).fetchone()[0])",
  "answer": "go 1\npy 1\ngo 2\ngo 3",
  "explanation": "The first 'go' and 'py' are inserted with 1. Each later 'go' hits the primary key, so the DO UPDATE branch adds 1 to the stored value, and RETURNING reports the new count." }
```

## 2. Upsert instead of check-then-insert

"Add a contact if it isn't there" written the obvious way is a SELECT, then an INSERT. Two requests can both see "not there" and both insert: one crashes with an IntegrityError, or, without a unique constraint, you get duplicates. Let the constraint decide instead:

```python
ADD = """INSERT INTO contacts (owner_id, contact_id, nickname) VALUES (?, ?, ?)
         ON CONFLICT (owner_id, contact_id) DO NOTHING
         RETURNING owner_id"""
print("first add: ", conn.execute(ADD, (1, 2, "Sara")).fetchone())
print("second add:", conn.execute(ADD, (1, 2, "S.")).fetchone())

SAVE = """INSERT INTO contacts (owner_id, contact_id, nickname) VALUES (?, ?, ?)
          ON CONFLICT (owner_id, contact_id) DO UPDATE SET nickname = excluded.nickname
          RETURNING nickname"""
print("save new:     ", conn.execute(SAVE, (1, 3, "Omid")).fetchone())
print("save existing:", conn.execute(SAVE, (1, 2, "Sara K.")).fetchone())
print(conn.execute("SELECT * FROM contacts ORDER BY contact_id").fetchall())
```

```console
first add:  (1,)
second add: None
save new:      ('Omid',)
save existing: ('Sara K.',)
[(1, 2, 'Sara K.'), (1, 3, 'Omid')]
```

- **The conflict target** `(owner_id, contact_id)` must match a PRIMARY KEY, UNIQUE constraint or unique index. Without one, there's nothing to conflict with.
- **`DO NOTHING`** skips the duplicate. With `RETURNING`, **no row means "it already existed"**: an idempotent "add" that can also tell you whether it did anything.
- **`DO UPDATE SET nickname = excluded.nickname`**: `excluded` is the row you *tried* to insert; a bare column name (or `contacts.nickname`) is the row already stored.
- The PostgreSQL docs guarantee that `ON CONFLICT DO UPDATE` ends in either an insert or an update atomically, "even under high concurrency". SQLite copied PostgreSQL's syntax, so this SQL is the same on both.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:', isolation_level=None)\nconn.execute('CREATE TABLE follows (a INTEGER, b INTEGER, PRIMARY KEY (a, b))')\nsql = 'INSERT INTO follows VALUES (?, ?) ON CONFLICT DO NOTHING RETURNING a'\nprint([conn.execute(sql, p).fetchone() for p in [(1, 2), (1, 2), (2, 1)]])",
  "answer": "[(1,), None, (2,)]",
  "explanation": "The duplicate (1, 2) is skipped, and DO NOTHING returns no row for it. (2, 1) is a different key, so it's inserted." }
```

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "In `ON CONFLICT (user_id) DO UPDATE SET score = excluded.score + scores.score`, what do `excluded.score` and `scores.score` refer to?",
  "options": ["excluded.score is the value you tried to insert; scores.score is the value already stored", "Both are the stored value", "excluded.score is the old value; scores.score is the new value", "excluded.score is NULL unless the row was deleted"], "answer": 0,
  "explanation": "excluded is the proposed row; the table name (or a bare column) is the existing row. This statement adds the new score to the stored one." }
```

## 3. Conditional upserts: never move backwards

Events arrive out of order. A phone reports "last seen 11:00", then a delayed request reports "09:00". A plain upsert would move the value backwards. Add a `WHERE` to `DO UPDATE`:

```python
SEEN = """INSERT INTO devices (user_id, device, last_seen) VALUES (?, ?, ?)
          ON CONFLICT (user_id, device) DO UPDATE SET last_seen = excluded.last_seen
          WHERE excluded.last_seen > devices.last_seen
          RETURNING last_seen"""
print(conn.execute(SEEN, (1, "phone", "2026-11-12 10:00")).fetchone())
print(conn.execute(SEEN, (1, "phone", "2026-11-12 11:00")).fetchone())
print(conn.execute(SEEN, (1, "phone", "2026-11-12 09:00")).fetchone())   # late, out-of-order event
print(conn.execute("SELECT last_seen FROM devices").fetchone())
```

```console
('2026-11-12 10:00',)
('2026-11-12 11:00',)
None
('2026-11-12 11:00',)
```

The late 09:00 event changed nothing. Note what RETURNING gave for it: **no row**, because when the WHERE is false the statement neither inserts nor updates. If you need the stored value back in every case, either SELECT it afterwards, or make the update always run but keep the larger value: SQLite's two-argument `max(a, b)`, which PostgreSQL spells `GREATEST(a, b)`. That spelling is one of the few places where the SQL differs between the two.

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "`DELETE FROM messages WHERE chat_id = ? RETURNING id` returns the deleted ids in ascending id order.", "answer": false,
  "explanation": "The SQLite docs say RETURNING rows come in arbitrary order, with no way to request an order. Sort them in Python if the order matters." }
```

## 4. The same upsert from SQLAlchemy, for both databases

SQLAlchemy exposes ON CONFLICT through the **dialect-specific** `insert()`: `sqlalchemy.dialects.sqlite.insert` and `sqlalchemy.dialects.postgresql.insert` have the same `on_conflict_do_update()` API. One function can build the statement for either:

```python
def save_contact_stmt(insert, owner_id, contact_id, nickname):
    stmt = insert(Contact).values(owner_id=owner_id, contact_id=contact_id, nickname=nickname)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Contact.owner_id, Contact.contact_id],
        set_={"nickname": stmt.excluded.nickname},
    )
    return stmt.returning(Contact.nickname)


with Session(engine) as session, session.begin():      # SQLite engine
    for nick in ("Sara", "Sara K."):
        print(session.execute(save_contact_stmt(sqlite.insert, 1, 2, nick)).scalar_one())

# Same statement built with the PostgreSQL dialect: compiled to SQL text only, not executed.
print(save_contact_stmt(postgresql.insert, 1, 2, "Sara").compile(dialect=postgresql.dialect()))
```

```console
Sara
Sara K.
INSERT INTO contacts (owner_id, contact_id, nickname) VALUES (%(owner_id)s::INTEGER, %(contact_id)s::INTEGER, %(nickname)s::VARCHAR) ON CONFLICT (owner_id, contact_id) DO UPDATE SET nickname = excluded.nickname RETURNING contacts.nickname
```

The first two lines ran on SQLite. The last line is the SQL SQLAlchemy **would send to PostgreSQL**: it was compiled here, not executed (no PostgreSQL on this machine). Apart from the parameter style (`%(name)s` with casts instead of `?`), it's the statement you just learned.

```quiz
{ "id": "q5", "type": "choice", "label": "Application",
  "prompt": "A mobile client retries `POST /chats/7/join` when the network drops, so the server sometimes gets the same request twice. Which implementation makes the endpoint safe to retry?",
  "options": ["INSERT ... ON CONFLICT (chat_id, user_id) DO NOTHING RETURNING ..., answering 201 if a row came back and 200 if not", "SELECT to check membership, then INSERT", "INSERT and let the IntegrityError propagate as a 500", "Delete the membership first, then insert it"], "answer": 0,
  "explanation": "The upsert is atomic and idempotent: a retry doesn't fail or duplicate, and RETURNING tells you which case happened. Check-then-insert races; a 500 on retry is wrong; delete-then-insert loses data such as joined_at." }
```

## 5. Your turn

Three writes, no read-before-write: `join_chat` (report whether it was new), `mark_read` (a read marker that never moves backwards, returning the stored value) and `delete_chat_messages` (return the deleted ids, and remember what RETURNING promises about order). The tests trace your SQL to check that each write is one statement.

```exercise
DB.M08.L02.E1
```

```quiz
{ "id": "q6", "type": "explain", "label": "Explain",
  "prompt": "Explain to a teammate why `SELECT ... ; if not found: INSERT` is wrong for 'add contact', and what to write instead.",
  "model": "Two concurrent requests can both run the SELECT before either INSERTs, so both try to insert: one fails with a unique violation, or you get duplicates if there's no constraint. Put a UNIQUE/PRIMARY KEY on (owner_id, contact_id) and write one statement: INSERT ... ON CONFLICT (owner_id, contact_id) DO NOTHING (or DO UPDATE to change the nickname), with RETURNING if you need to know whether it inserted. The database makes it atomic.",
  "explanation": "The constraint plus ON CONFLICT replaces the racy check." }
```
