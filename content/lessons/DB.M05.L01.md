---
{
  "id": "DB.M05.L01",
  "title": "How SQLite finds rows: scans, B-tree indexes and EXPLAIN QUERY PLAN",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["DB.M04"],
  "objectives": [
    "Explain why a full table scan costs time proportional to the row count, while an index lookup costs about log N",
    "Run EXPLAIN QUERY PLAN from Python and read SCAN, SEARCH, USING INDEX, USING INTEGER PRIMARY KEY and USE TEMP B-TREE",
    "Predict which indexes already exist because of PRIMARY KEY and UNIQUE constraints",
    "Recognise WHERE clauses that can't use an index (a function or arithmetic on the column) and check them with a plan"
  ],
  "why": "In your Go services an index migration was something the AI wrote. Here you learn to ask the database how it will run a query before you guess. Every later performance question in this course (and every slow-query log you'll read at work) starts with reading a plan.",
  "applications": [
    "Checking a new endpoint's query before it reaches production",
    "Explaining a slow query in a code review with evidence instead of a hunch",
    "Writing tests that fail if a query stops using its index"
  ],
  "exercises": ["DB.M05.L01.E1"],
  "sources": [
    {
      "title": "The SQLite Query Optimizer: Query Planning",
      "url": "https://www.sqlite.org/queryplanner.html",
      "version": "SQLite docs, page updated 2026-03-22; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["A full table scan reads and examines every row", "A rowid lookup is a binary search, proportional to log N", "An index is a separate table holding the indexed columns followed by the rowid, kept in sorted order"]
    },
    {
      "title": "EXPLAIN QUERY PLAN",
      "url": "https://www.sqlite.org/eqp.html",
      "version": "SQLite docs, page updated 2025-05-31; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["Each plan row has a node id, a parent id, an unused field and a detail description", "SCAN is a full-table scan (also when iterating in index order); SEARCH visits only a subset of rows", "USE TEMP B-TREE FOR ORDER BY means a separate sort step", "The output format is for debugging and may change between releases"]
    },
    {
      "title": "CREATE TABLE",
      "url": "https://www.sqlite.org/lang_createtable.html",
      "version": "SQLite docs, page updated 2025-04-30; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["UNIQUE and PRIMARY KEY constraints are usually implemented with a unique index", "A single-column INTEGER PRIMARY KEY is an alias for the rowid (and needs no separate index)"]
    },
    {
      "title": "The SQLite Query Optimizer Overview",
      "url": "https://www.sqlite.org/optoverview.html",
      "version": "SQLite docs, page updated 2025-05-31; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["The initial columns of an index must be used with =, IN or IS; there can be no gaps in the used columns"]
    }
  ]
}
---
## 1. Without an index, the database reads everything

Recap from DB.M01–DB.M04: you have the messaging schema (`users`, `chats`, `chat_members`, `messages`) and you query it from Python with `?` placeholders. This module asks a new question: **how much work does a query cost?**

Picture `messages` as a Go slice of structs. To find the messages sent by user 7 you write a `for` loop over the whole slice: the cost grows with the length. That's a **full table scan**: SQLite reads and checks every row.

Now picture a sorted slice of `(sender_id, id)` pairs kept next to the table. You binary-search it for `7` (`sort.Search` in Go), get the matching ids, and fetch only those rows. That sorted copy is an **index**. SQLite stores tables and indexes as B-trees, so a lookup costs about **log N** steps instead of N. With a million rows that's about 20 steps instead of a million.

Two consequences you'll use all module:

- An index is a **separate structure the database must keep sorted**, so every INSERT, UPDATE and DELETE also updates it (L03 measures that cost).
- An index helps only if the query's shape lets SQLite **binary-search** it. Most of this module is about that "if".

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "`messages` grows from 10,000 rows to 10,000,000 rows. Roughly how does the cost of `SELECT * FROM messages WHERE sender_id = ?` change if there is no index on sender_id?",
  "options": ["About 1000 times more work: every row is read", "About the same: SQLite caches the answer", "About 3 times more work, like a binary search", "It depends only on how many rows match"], "answer": 0,
  "explanation": "Without an index the only plan is a full scan, and its cost is proportional to the table size. With an index the lookup grows like log N, which barely moves between 10 thousand and 10 million." }
```

## 2. Ask SQLite: EXPLAIN QUERY PLAN

Put `EXPLAIN QUERY PLAN` in front of a statement and SQLite **plans it without running it**, returning the plan as rows:

```python
import sqlite3
from pathlib import Path

conn = sqlite3.connect(":memory:")
conn.executescript(Path("schema.sql").read_text())   # the messaging schema

for row in conn.execute("EXPLAIN QUERY PLAN SELECT * FROM messages WHERE sender_id = ?", (7,)):
    print(row)
```

```console
(2, 0, 0, 'SCAN messages')
```

Each row has four fields: a node id, its parent node id (plans are trees; joins and subqueries add children), an unused field, and the **detail**, the part you read. The ids may differ on your machine; the detail is what matters.

The two words to know first:

- **`SCAN t`**: a full scan. Every row of `t` is visited (also when SQLite walks a whole index in order).
- **`SEARCH t ...`**: only a subset of rows is visited, found through an index or the primary key.

The bound value never appears in the plan; it shows `?`. That's fine: the plan depends on the *shape* of the query, which is one more reason to keep using placeholders.

The SQLite docs warn that this output is for debugging and **its format may change between releases** (it changed a lot in 3.24.0). Read it, test with it, but don't parse it in production code. This machine runs SQLite 3.45.1.

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "`conn.execute(\"EXPLAIN QUERY PLAN DELETE FROM messages\")` deletes every message, then shows the plan it used.", "answer": false,
  "explanation": "EXPLAIN QUERY PLAN only plans the statement and returns the plan as rows. Nothing is executed, so nothing is deleted." }
```

## 3. Reading the common details

A small helper that prints only the detail column, run against the schema with no extra indexes:

```python
def show(sql, params=()):
    print(sql)
    for _id, _parent, _unused, detail in conn.execute("EXPLAIN QUERY PLAN " + sql, params):
        print("   ", detail)

show("SELECT * FROM messages WHERE id = ?", (1,))
show("SELECT * FROM users WHERE username = ?", ("ali",))
show("SELECT * FROM chat_members WHERE chat_id = ?", (3,))
show("SELECT * FROM chat_members WHERE user_id = ?", (7,))
show("SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at", (3,))
```

```console
SELECT * FROM messages WHERE id = ?
    SEARCH messages USING INTEGER PRIMARY KEY (rowid=?)
SELECT * FROM users WHERE username = ?
    SEARCH users USING INDEX sqlite_autoindex_users_1 (username=?)
SELECT * FROM chat_members WHERE chat_id = ?
    SEARCH chat_members USING INDEX sqlite_autoindex_chat_members_1 (chat_id=?)
SELECT * FROM chat_members WHERE user_id = ?
    SCAN chat_members
SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at
    SCAN messages
    USE TEMP B-TREE FOR ORDER BY
```

What each line tells you:

1. **`USING INTEGER PRIMARY KEY (rowid=?)`**: `id INTEGER PRIMARY KEY` *is* the rowid, the key the table itself is sorted by. No extra index is needed.
2. **`sqlite_autoindex_users_1`**: you never wrote `CREATE INDEX`, but `username TEXT UNIQUE` needs a fast "does this already exist?" check, so SQLite built a unique index for it. PRIMARY KEY constraints (other than INTEGER PRIMARY KEY) get one too.
3. **`(chat_id=?)`** in brackets: which index columns the search uses.
4. **`SCAN chat_members`** for `user_id`: the composite primary key is `(chat_id, user_id)`, sorted by `chat_id` first. Finding a `user_id` in it is like finding everyone named "Ali" in a phone book sorted by surname: you read the whole book. The "my chats" query needs its own index. L02 is all about this column-order rule.
5. **`USE TEMP B-TREE FOR ORDER BY`**: after finding the rows, SQLite sorts them in a temporary structure. That's an extra step whose cost grows with the number of matching rows.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT)')\nfor *_, detail in conn.execute('EXPLAIN QUERY PLAN SELECT name FROM users WHERE email = ?', ('a@b.c',)):\n    print(detail)",
  "answer": "SEARCH users USING INDEX sqlite_autoindex_users_1 (email=?)",
  "explanation": "The UNIQUE constraint on email made SQLite create sqlite_autoindex_users_1, and the equality filter on email can binary-search it, so the plan is a SEARCH." }
```

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('CREATE TABLE chat_members (chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, PRIMARY KEY (chat_id, user_id))')\nfor *_, detail in conn.execute('EXPLAIN QUERY PLAN SELECT chat_id FROM chat_members WHERE user_id = ?', (7,)):\n    print(detail)",
  "answer": "SCAN chat_members",
  "explanation": "The primary key index is sorted by chat_id first, so a filter on user_id alone can't binary-search it. The plan reads every row." }
```

## 4. Adding an index, and how to defeat it by accident

`CREATE INDEX name ON table (columns)` builds the sorted structure from section 1. Name indexes after table and columns (`idx_messages_sender`) so a plan tells you which one was chosen.

```python
conn.execute("CREATE INDEX idx_messages_sender ON messages (sender_id)")

show("SELECT * FROM messages WHERE sender_id = ?", (7,))
show("SELECT * FROM messages WHERE sender_id + 0 = ?", (7,))
show("SELECT * FROM users WHERE lower(username) = ?", ("ali",))
show("SELECT * FROM messages WHERE CAST(sender_id AS TEXT) = ?", ("7",))
```

```console
SELECT * FROM messages WHERE sender_id = ?
    SEARCH messages USING INDEX idx_messages_sender (sender_id=?)
SELECT * FROM messages WHERE sender_id + 0 = ?
    SCAN messages
SELECT * FROM users WHERE lower(username) = ?
    SCAN users
SELECT * FROM messages WHERE CAST(sender_id AS TEXT) = ?
    SCAN messages
```

The index is sorted by `sender_id`, not by `sender_id + 0` or `lower(username)`. Once you wrap the column in an expression, SQLite can't binary-search for the result, so it falls back to a scan. The fix is to keep the column bare and move the work to the value side: store usernames already lowercased and compare with `username = ?` after lowercasing the input in Python.

**Common mistakes**

- Assuming "there's an index on that column" means "this query uses it". Check the plan.
- Adding an index for a query on a 50-row table. A scan of 50 rows is already instant; L03 shows how to decide with numbers.
- Reading the plan of a query you wrote by hand instead of the exact SQL your code sends (copy it from the code, or log it).

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "There's an index on `users(email)`. Login is slow, and the code runs `SELECT id FROM users WHERE upper(email) = upper(?)`. What does the plan most likely show, and what's the fix?",
  "options": ["SCAN users; store emails normalised and compare `email = ?` with the input normalised in Python", "SEARCH users USING INDEX; the slowness is elsewhere", "SCAN users; add a second index on email", "SEARCH users; switch to LIKE"], "answer": 0,
  "explanation": "upper(email) is an expression on the column, so the index on email can't be searched for it. A second identical index changes nothing. Normalise once on write, then compare the bare column." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "A teammate says: 'username is UNIQUE, so we should also CREATE INDEX on username to make login fast.' What do you answer, and how would you prove it?",
  "model": "Not needed: the UNIQUE constraint already created a unique index (sqlite_autoindex_users_N). Prove it with EXPLAIN QUERY PLAN on the login query: it shows SEARCH users USING INDEX sqlite_autoindex_users_1 (username=?). A second index on the same column would only slow down writes.",
  "explanation": "UNIQUE and non-integer PRIMARY KEY constraints come with their own index." }
```

## 5. Your turn

You'll use plans in tests for the rest of this module, so build the helper yourself: `explain()` returns the detail lines and `full_scans()` lists the tables read with a SCAN. Use what you learned in sections 2 and 3, and remember the edge cases: no parameters, a query with no table at all, and aliases in a JOIN.

```exercise
DB.M05.L01.E1
```
