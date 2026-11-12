---
{
  "id": "DB.M01.L02",
  "title": "Writing rows: INSERT, UPDATE, DELETE and constraints",
  "difficulty": "beginner",
  "minutes": 50,
  "prerequisites": ["DB.M01.L01"],
  "objectives": [
    "Write INSERT with an explicit column list, and read the new id from cursor.lastrowid",
    "Predict which constraint (NOT NULL, UNIQUE, CHECK) rejects a write, the sqlite3 exception it raises, and what's left in the table afterwards",
    "Write UPDATE and DELETE whose WHERE pins down exactly the intended rows, and use cursor.rowcount to check what happened",
    "Explain why a statement that matches zero rows succeeds, and where your code has to handle that case"
  ],
  "why": "Reads that go wrong show a wrong screen; writes that go wrong destroy data. A missing WHERE or an OR instead of an AND rewrites a whole table, and nothing warns you. Constraints are the database's own checks, so it's worth knowing exactly what they reject.",
  "applications": [
    "Sign-up: inserting a user and turning a duplicate username into a clean error",
    "Editing or deleting one message by id, and answering 404 when it doesn't exist",
    "Membership changes: joining and leaving chats"
  ],
  "exercises": ["DB.M01.L02.E1"],
  "sources": [
    {
      "title": "SQLite: CREATE TABLE",
      "url": "https://www.sqlite.org/lang_createtable.html",
      "version": "SQLite docs (current); behaviour checked locally on SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["NOT NULL, UNIQUE and CHECK violations on insert or update are constraint violations", "Without a DEFAULT clause a column's default is NULL", "The default conflict resolution algorithm is ABORT", "A single-column INTEGER PRIMARY KEY is an alias for the rowid"]
    },
    {
      "title": "SQLite: ON CONFLICT clause",
      "url": "https://www.sqlite.org/lang_conflict.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["ABORT backs out the changes made by the current statement; earlier statements in the same transaction are preserved"]
    },
    {
      "title": "SQLite: UPDATE",
      "url": "https://www.sqlite.org/lang_update.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["Without a WHERE clause, all rows are modified", "A WHERE that matches no row is not an error; zero rows are affected"]
    },
    {
      "title": "SQLite: DELETE",
      "url": "https://www.sqlite.org/lang_delete.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["Without a WHERE clause, all records in the table are deleted"]
    },
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["lastrowid is the row id of the last row inserted by execute()", "rowcount is the number of modified rows for INSERT, UPDATE, DELETE and REPLACE", "IntegrityError is raised when relational integrity is affected and is a subclass of DatabaseError"]
    }
  ]
}
---
## 1. INSERT: always name the columns

```python
import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("""
CREATE TABLE customers (
    id      INTEGER PRIMARY KEY,
    email   TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL DEFAULT 'DE',
    credits INTEGER NOT NULL DEFAULT 0 CHECK (credits >= 0)
)""")
cur = conn.execute("INSERT INTO customers (email) VALUES (?)", ("kim@example.com",))
print(cur.lastrowid, cur.rowcount)
cur = conn.execute("INSERT INTO customers (email, country) VALUES (?, ?), (?, ?)",
                   ("lee@example.com", "FR", "park@example.com", "KR"))
print(cur.rowcount)
print(conn.execute("SELECT * FROM customers ORDER BY id").fetchall())
```

```text
1 1
2
[(1, 'kim@example.com', 'DE', 0), (2, 'lee@example.com', 'FR', 0), (3, 'park@example.com', 'KR', 0)]
```

- **Columns you leave out get their DEFAULT,** or NULL if there's no DEFAULT. `country` and `credits` were filled in for you.
- **`id INTEGER PRIMARY KEY`** is SQLite's auto-increment column: leave it out and SQLite picks the id. `cur.lastrowid` tells you which, like `LastInsertId()` in Go. (MySQL spells this `AUTO_INCREMENT`.)
- One INSERT can add several rows; `rowcount` says how many.

Without a column list, VALUES must give **every** column in table order:

```python
try:
    conn.execute("INSERT INTO customers VALUES (?, ?)", ("x@example.com", "US"))
except sqlite3.OperationalError as e:
    print("OperationalError:", e)
```

```text
OperationalError: table customers has 4 columns but 2 values were supplied
```

That's the lucky case. The unlucky case is when the counts happen to match and the values land in the wrong columns, or when someone adds a column next month and every positional INSERT breaks. Name your columns.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE tags(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)')\ncur = c.execute('INSERT INTO tags (name) VALUES (?), (?), (?)', ('go', 'sql', 'py'))\nprint(cur.lastrowid, cur.rowcount)",
  "answer": "3 3",
  "explanation": "Three rows inserted (rowcount 3); SQLite assigned ids 1, 2, 3, and lastrowid is the last one." }
```

## 2. Constraints: the database says no

A constraint is a rule the database checks on **every** write, whichever program does the writing. When a write breaks one, sqlite3 raises `sqlite3.IntegrityError`, which you handle like any exception from PY.M04:

```python
for bad in [("kim@example.com", 0), (None, 0), ("new@example.com", -5)]:
    try:
        conn.execute("INSERT INTO customers (email, credits) VALUES (?, ?)", bad)
    except sqlite3.IntegrityError as e:
        print("IntegrityError:", e)
print(conn.execute("SELECT count(*) FROM customers").fetchone()[0])
```

```text
IntegrityError: UNIQUE constraint failed: customers.email
IntegrityError: NOT NULL constraint failed: customers.email
IntegrityError: CHECK constraint failed: credits >= 0
3
```

Python's `None` is SQL NULL, so `(None, 0)` hits NOT NULL. The table still has 3 rows: by default (SQLite calls it ABORT), a failing statement is **backed out completely**, even rows of a multi-row INSERT that were fine. Only that statement is undone; earlier statements are not. DB.M03 builds on exactly that distinction.

**In Go terms:** MySQL's "Duplicate entry ... for key" error is the same idea. Catch the narrow class (`sqlite3.IntegrityError`), not `Exception`, and turn it into a domain error such as `UsernameTaken`, as in PY.M04.L03.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE tags(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)')\nc.execute('INSERT INTO tags (name) VALUES (?), (?)', ('go', 'sql'))\ntry:\n    c.execute('INSERT INTO tags (name) VALUES (?), (?)', ('py', 'go'))\nexcept sqlite3.IntegrityError as e:\n    print(e)\nprint(c.execute('SELECT count(*) FROM tags').fetchone()[0])",
  "answer": "UNIQUE constraint failed: tags.name\n2",
  "explanation": "The second INSERT fails on 'go'. The whole statement is backed out, so 'py' isn't kept either: 2 rows. The first INSERT, a separate statement, is not affected." }
```

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "Sign-up code must reject a username that's already taken, even when two requests arrive at the same moment. Where should the rule live?",
  "options": ["A SELECT before the INSERT, in Python", "A UNIQUE constraint on username, with the IntegrityError turned into a 'name taken' error", "A comment in the schema", "A Python set of known usernames"], "answer": 1,
  "explanation": "Check-then-insert in Python has a gap: both requests can pass the SELECT before either INSERTs. The constraint is checked by the database on every write, so it can't be skipped." }
```

## 3. UPDATE: the WHERE is the whole point

```python
cur = conn.execute("UPDATE customers SET credits = credits + ? WHERE country = ?", (10, "FR"))
print("updated", cur.rowcount)
cur = conn.execute("UPDATE customers SET credits = 5 WHERE id = ?", (99,))
print("updated", cur.rowcount)
cur = conn.execute("UPDATE customers SET country = 'US'")
print("updated", cur.rowcount)
print(conn.execute("SELECT id, country, credits FROM customers ORDER BY id").fetchall())
```

```text
updated 1
updated 0
updated 3
[(1, 'US', 0), (2, 'US', 10), (3, 'US', 0)]
```

- `SET credits = credits + ?` computes from the row's current value, inside the database. No read-modify-write in Python (DB.M06 shows why that matters with concurrent users).
- **Zero matching rows is a success** with `rowcount == 0`. Like `RowsAffected()` in Go, it's your code's job to notice. An API would answer 404.
- **No WHERE means every row.** The third UPDATE moved every customer to the US, and nothing warned about it.

A habit that prevents this: write the WHERE first, and try it as a `SELECT count(*) ... WHERE ...` before turning it into an UPDATE or DELETE.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE stock(sku TEXT PRIMARY KEY, qty INTEGER NOT NULL);\nINSERT INTO stock VALUES ('a', 3), ('b', 0), ('c', 5);''')\ncur = c.execute('UPDATE stock SET qty = qty - 1 WHERE qty > 0')\nprint(cur.rowcount, c.execute('SELECT qty FROM stock ORDER BY sku').fetchall())",
  "answer": "2 [(2,), (0,), (4,)]",
  "explanation": "Only a and c have qty > 0, so 2 rows change. b stays at 0." }
```

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "`UPDATE messages SET body = ? WHERE id = ?` with an id that doesn't exist raises an exception.", "answer": false,
  "explanation": "It succeeds and changes 0 rows (rowcount 0). If 'not found' matters, check rowcount yourself." }
```

## 4. DELETE: same rules

```python
cur = conn.execute("DELETE FROM customers WHERE credits = ?", (0,))
print("deleted", cur.rowcount)
print(conn.execute("SELECT id, email FROM customers").fetchall())
```

```text
deleted 2
[(2, 'lee@example.com')]
```

DELETE removes every row its WHERE is true for, and **all** rows without a WHERE. Watch AND vs OR. "Delete user 7's session 3" is `user_id = ? AND id = ?`; with OR it deletes all of user 7's sessions *and* session 3, whoever owns it.

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE sessions(id INTEGER PRIMARY KEY, user_id INTEGER, expired INTEGER);\nINSERT INTO sessions(user_id, expired) VALUES (1, 1), (2, 0), (1, 0);''')\nprint(c.execute('DELETE FROM sessions WHERE user_id = ? AND expired = 1', (2,)).rowcount, c.execute('DELETE FROM sessions').rowcount, c.execute('SELECT count(*) FROM sessions').fetchone()[0])",
  "answer": "0 3 0",
  "explanation": "User 2 has no expired session, so 0 rows. The DELETE without WHERE removes all 3 rows, and the table is empty." }
```

## 5. One thing this lesson skips on purpose

Every example here uses one connection to an in-memory database, so it sees its own writes immediately. Whether a write is **permanently saved**, and what a crash halfway through several writes leaves behind, depends on transactions and `commit()`. That's DB.M03, and it's where your assessment question about two DELETEs and a crash gets answered properly. Until then, don't assume either way.

## 6. Your turn

This is a **debug** exercise: three statements from a chat backend, each with one bug. Run pytest first and read the failures: two of them fail with a database error that names the problem, and one runs fine but touches the wrong rows.

```exercise
DB.M01.L02.E1
```
