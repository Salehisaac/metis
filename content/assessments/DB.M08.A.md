---
{ "id": "DB.M08.A", "module": "DB.M08", "title": "DB.M08 module assessment: PostgreSQL specifics", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before moving on.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "A conditional upsert. What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:', isolation_level=None)\nconn.execute('CREATE TABLE scores (user_id INTEGER PRIMARY KEY, best INTEGER NOT NULL)')\nsql = ('INSERT INTO scores VALUES (?, ?) ON CONFLICT (user_id) DO UPDATE SET best = excluded.best '\n       'WHERE excluded.best > scores.best RETURNING best')\nprint([conn.execute(sql, p).fetchone() for p in [(1, 50), (1, 80), (1, 60)]])",
  "answer": "[(50,), (80,), None]",
  "explanation": "50 is inserted, 80 beats it and updates, 60 doesn't pass the WHERE, so nothing is written and RETURNING gives no row." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "ON DELETE CASCADE in SQLite, on a fresh connection. What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('CREATE TABLE parents (id INTEGER PRIMARY KEY)')\nconn.execute('CREATE TABLE kids (id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL REFERENCES parents(id) ON DELETE CASCADE)')\nconn.execute('INSERT INTO parents VALUES (1)')\nconn.execute('INSERT INTO kids (parent_id) VALUES (1), (1)')\nconn.execute('DELETE FROM parents WHERE id = 1')\nprint(conn.execute('SELECT count(*) FROM kids').fetchone()[0])",
  "answer": "2",
  "explanation": "Foreign keys, including their ON DELETE actions, are off until PRAGMA foreign_keys = ON runs on the connection. The kids survive as orphans. PostgreSQL would have deleted them." }
```

```quiz
{ "id": "a3", "type": "choice",
  "prompt": "`price INTEGER CHECK (price > 0)`. Which insert succeeds?",
  "options": ["INSERT ... VALUES (NULL)", "INSERT ... VALUES (0)", "INSERT ... VALUES (-5)", "None of them"], "answer": 0,
  "explanation": "A CHECK fails only when its expression is false; NULL > 0 is NULL. Add NOT NULL if a price is required." }
```

```quiz
{ "id": "a4", "type": "choice", "label": "Application",
  "prompt": "Rule: a chat can have many invites for a user, but at most one with status 'pending'. Which enforces it in the database?",
  "options": ["CREATE UNIQUE INDEX ... ON chat_invites (chat_id, invitee_id) WHERE status = 'pending'", "UNIQUE (chat_id, invitee_id, status)", "UNIQUE (chat_id, invitee_id)", "A CHECK (status = 'pending')"], "answer": 0,
  "explanation": "A partial unique index constrains only pending rows. UNIQUE over the three columns would also forbid two declined invites; over two columns it forbids any history." }
```

```quiz
{ "id": "a5", "type": "truefalse",
  "prompt": "In PostgreSQL, `INSERT ... ON CONFLICT (id) DO UPDATE ...` can be replaced by a SELECT followed by either an INSERT or an UPDATE without losing anything.", "answer": false,
  "explanation": "The two-step version races: concurrent requests can both see 'missing' and both insert. ON CONFLICT DO UPDATE guarantees an atomic insert-or-update outcome." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Your service moves from SQLite to PostgreSQL. Name three things from this module you'd check or change, and why.",
  "model": "1) Foreign keys and types: PostgreSQL enforces both strictly, so data that SQLite accepted (orphans without the PRAGMA, text in integer columns) will fail; clean it before migrating and use STRICT/PRAGMA in tests. 2) Dialect differences in SQL: SQLite's max(a, b) becomes GREATEST(a, b); SQLAlchemy's sqlite.insert becomes postgresql.insert for ON CONFLICT. 3) JSON: TEXT JSON becomes jsonb, with @> and a GIN index where containment queries are hot; SQLite's 'JSONB' format is unrelated. Also: run the database in Docker with a named volume, and run the test suite against it in CI.",
  "explanation": "Constraint enforcement, dialect-specific SQL and JSON storage are the main differences, and a real PostgreSQL in CI catches the rest." }
```
