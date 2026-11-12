---
{
  "id": "DB.M08.L03",
  "title": "JSONB and partial indexes: when they're justified",
  "difficulty": "intermediate",
  "minutes": 80,
  "prerequisites": ["DB.M08.L02"],
  "objectives": [
    "Decide between ordinary columns and a JSON(B) column for a piece of data, with reasons",
    "Query and update JSON in SQLite (->, ->>, json_set, json_valid) and read the PostgreSQL JSONB equivalents (@>, GIN index)",
    "Create a partial index and a partial unique index, and check with EXPLAIN QUERY PLAN when the planner uses it",
    "Know the portability traps: SQLite's JSONB isn't PostgreSQL's, and partial-index predicates must match the query"
  ],
  "why": "JSONB and partial indexes are two PostgreSQL features that are easy to overuse or to miss entirely. Used well, a JSONB column holds genuinely variable data (attachment metadata, user settings), and a partial index enforces a rule like 'one pinned message per chat' that no plain constraint can express. The module's outcome is to use them where justified, so most of this lesson is about when.",
  "applications": [
    "Message attachments whose fields differ by type (photo, voice, file)",
    "User preferences that change shape over time",
    "Rules over a subset of rows: one active invite, one pinned message, one default address"
  ],
  "exercises": ["DB.M08.L03.E1"],
  "sources": [
    {
      "title": "PostgreSQL 18 Documentation: 8.14 JSON Types",
      "url": "https://www.postgresql.org/docs/current/datatype-json.html",
      "version": "PostgreSQL 18 (docs 18.7); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["json stores the input text; jsonb a decomposed binary form, slower to input, faster to process, indexable", "jsonb drops whitespace, key order and duplicate keys (last wins)", "Most applications should prefer jsonb", "@> tests containment", "The default GIN operator class supports ?, ?|, ?&, @>, @? and @@; jsonb_path_ops supports @>, @? and @@", "Any update locks the whole row; keep JSON documents to a manageable, atomic size"]
    },
    {
      "title": "PostgreSQL 18 Documentation: 11.8 Partial Indexes",
      "url": "https://www.postgresql.org/docs/current/indexes-partial.html",
      "version": "PostgreSQL 18 (docs 18.7); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["A partial index covers only rows satisfying its predicate", "It avoids indexing common values, is smaller and makes many updates cheaper", "A partial unique index enforces uniqueness only among rows that satisfy the predicate", "The query's WHERE must imply the predicate; matching happens at planning time, so parameterized clauses don't match", "Partial indexes aren't a substitute for partitioning"]
    },
    {
      "title": "Partial Indexes (SQLite)",
      "url": "https://www.sqlite.org/partialindex.html",
      "version": "SQLite docs, page updated 2022-04-18; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["A partial index is created by adding WHERE to CREATE INDEX; supported since 3.8.0", "The planner uses it when the query's WHERE terms imply the index's WHERE; terms must match exactly", "UNIQUE partial indexes require uniqueness only among indexed rows (one team leader per team)", "The index WHERE may not contain bound parameters"]
    },
    {
      "title": "JSON Functions And Operators (SQLite)",
      "url": "https://www.sqlite.org/json1.html",
      "version": "SQLite docs; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["JSON functions are built in since 3.38.0", "-> returns a JSON text representation; ->> returns an SQL TEXT, INTEGER, REAL or NULL value; both aim at MySQL/PostgreSQL compatibility", "SQLite's JSONB (3.45.0) is not binary compatible with PostgreSQL's JSONB"]
    },
    {
      "title": "CREATE INDEX (SQLite)",
      "url": "https://www.sqlite.org/lang_createindex.html",
      "version": "SQLite docs; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["An index key can list columns and/or expressions", "A WHERE clause makes it a partial index", "UNIQUE forbids duplicate index entries"]
    }
  ]
}
---
## 1. Columns first; JSON when the shape really varies

A JSON column is tempting: no migration when a field is added. But everything from this course works best on ordinary columns: types, NOT NULL, CHECK, foreign keys (L01), composite indexes (DB.M05), clear SQL. Use this test:

| Put it in a **column** when you... | A **JSON** column is justified when... |
|---|---|
| filter, sort, join or aggregate on it often | the fields differ by row type (photo vs voice vs file attachment) |
| need a constraint or foreign key on it | the data is sparse: most rows have none of 30 optional settings |
| every row has it | you store it and hand it back mostly as one piece |

The PostgreSQL docs add a reason to keep documents small: any update locks the whole row, so a document should be "an atomic datum" that isn't edited piece by piece by different transactions.

In the messenger, `chat_id`, `sender_id` and `created_at` are columns. An attachment's metadata (photo size, voice duration, file name) is a good JSON candidate.

```quiz
{ "id": "q1", "type": "choice", "label": "Application",
  "prompt": "A teammate wants `messages(id, data JSONB)` with chat_id, sender_id, body and created_at all inside data, 'so we never need migrations'. What's the main problem?",
  "options": ["You lose foreign keys, NOT NULL, simple composite indexes and clear SQL on the fields every query filters by", "JSONB can't store strings", "PostgreSQL limits a table to one JSONB column", "Nothing; it's the recommended design"], "answer": 0,
  "explanation": "Fields that every row has and every query filters or joins on belong in columns. JSON is for the variable part, like attachment metadata." }
```

## 2. JSON in SQLite (runnable here)

SQLite (3.38+) has JSON built in. `->` returns JSON text and `->>` returns an SQL value, an operator pair modelled to be compatible with PostgreSQL and MySQL:

```python
conn.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, body TEXT NOT NULL, "
             "attachment TEXT CHECK (attachment IS NULL OR json_valid(attachment)))")
conn.executemany("INSERT INTO messages (chat_id, body, attachment) VALUES (?, ?, ?)", [
    (1, "see photo", json.dumps({"type": "photo", "width": 1280, "height": 720})),
    (1, "voice", json.dumps({"type": "voice", "seconds": 12, "transcribed": True})),
    (1, "plain text", None),
    (2, "file", json.dumps({"type": "file", "name": "plan.pdf", "bytes": 48213})),
])

for row in conn.execute("SELECT id, attachment ->> '$.type', attachment -> '$.seconds', "
                        "attachment ->> '$.transcribed' FROM messages"):
    print(row)

print(conn.execute("SELECT body FROM messages WHERE attachment ->> '$.type' = ?", ("voice",)).fetchall())
conn.execute("UPDATE messages SET attachment = json_set(attachment, '$.seconds', 13) WHERE id = 2")
print(conn.execute("SELECT attachment FROM messages WHERE id = 2").fetchone()[0])
try:
    conn.execute("INSERT INTO messages (chat_id, body, attachment) VALUES (1, 'bad', '{oops')")
except sqlite3.IntegrityError as e:
    print("refused:", e)
```

```console
(1, 'photo', None, None)
(2, 'voice', '12', 1)
(3, None, None, None)
(4, 'file', None, None)
[('voice',)]
{"type":"voice","seconds":13,"transcribed":true}
refused: CHECK constraint failed: attachment IS NULL OR json_valid(attachment)
```

- `->>` gave `'photo'` (text) and `1` for JSON `true`; `->` gave `'12'`, the JSON *text* of the number.
- A missing key, or a NULL document, gives NULL. Use `coalesce(..., default)` when "missing" should mean a default.
- `json_set` changes one field in place, in SQL.
- SQLite stores JSON as TEXT, so a `CHECK (json_valid(...))` is your type check.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:')\ndoc = '{\"type\": \"photo\", \"size\": {\"w\": 800, \"h\": 600}, \"hd\": false}'\nprint(conn.execute(\"SELECT ? ->> '$.type', ? ->> '$.size.w', ? ->> '$.hd', ? ->> '$.missing'\", (doc, doc, doc, doc)).fetchone())",
  "answer": "('photo', 800, 0, None)",
  "explanation": "->> returns SQL values: text, an integer from a nested path, 0 for JSON false, and NULL for a missing key." }
```

## 3. JSONB in PostgreSQL (not run here)

**Not run on this machine (PostgreSQL unavailable); behaviour per the cited docs.**

- `json` stores the text as given; **`jsonb`** stores a parsed binary form: slower to write, faster to query, and **indexable**. It drops whitespace, key order and duplicate keys. The docs: most applications should prefer `jsonb`.
- **Containment** `@>` asks "does this document contain this fragment?", and a **GIN index** makes it fast:

```sql
CREATE TABLE messages (
    id         serial PRIMARY KEY,
    chat_id    integer NOT NULL REFERENCES chats(id),
    body       text NOT NULL,
    attachment jsonb
);
CREATE INDEX ix_messages_attachment ON messages USING gin (attachment);

SELECT id FROM messages WHERE attachment @> '{"type": "voice"}';   -- can use the GIN index
SELECT attachment ->> 'type' FROM messages WHERE id = 42;           -- ->> works as in SQLite
```

SQLAlchemy has a `JSONB` type for PostgreSQL. Compiled here, offline, without a database:

```console
SELECT messages.id
FROM messages
WHERE messages.attachment @> %(attachment_1)s::JSONB
CREATE INDEX ix_messages_attachment ON messages USING gin (attachment)
```

(from `select(Message.id).where(Message.attachment.contains({"type": "voice"}))` and an `Index(..., postgresql_using="gin")`).

**Portability trap:** SQLite 3.45 also has something called "JSONB", but its docs say it is not binary compatible with PostgreSQL's. Same name, different thing. Write portable code against `->>` and plain JSON text, and keep `@>`/GIN for PostgreSQL-only paths.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "PostgreSQL's jsonb keeps the order of keys exactly as you inserted them.", "answer": false,
  "explanation": "jsonb stores a decomposed binary form and doesn't preserve whitespace, key order or duplicate keys. The json type keeps the exact input text." }
```

## 4. Partial indexes: index only the rows that matter

A partial index has a `WHERE`: it contains only matching rows. Two uses:

- **Smaller, faster indexes** for queries that always target a small subset ("pending" jobs among millions of finished ones). The PostgreSQL docs: it avoids indexing common values and makes many updates cheaper.
- **Uniqueness over a subset**, which no plain UNIQUE can express. Here: at most one **pending** invite per (chat, invitee), but any number of old declined ones:

```python
conn.execute("CREATE UNIQUE INDEX uq_invites_pending ON chat_invites (chat_id, invitee_id) "
             "WHERE status = 'pending'")
```

```console
ok      1 7 declined
ok      1 7 declined
ok      1 7 pending
refused 1 7 pending -> UNIQUE constraint failed: chat_invites.chat_id, chat_invites.invitee_id
ok      2 7 pending
```

When does the planner use it? Only when the query's WHERE **implies** the index's WHERE:

```console
SELECT id FROM chat_invites WHERE chat_id = ? AND invitee_id = ? AND status = 'pending'
    ['SEARCH chat_invites USING COVERING INDEX uq_invites_pending (chat_id=? AND invitee_id=?)']
SELECT id FROM chat_invites WHERE chat_id = ? AND invitee_id = ?
    ['SCAN chat_invites']
```

Without `status = 'pending'` the index can't answer the query (it doesn't contain the other rows), so it's a SCAN. The SQLite docs add that the terms must match exactly; it does no algebra.

**Bound parameters for the predicate column:** with `status = ?` bound to `'pending'`, SQLite on this machine still chose the partial index, and bound to `'accepted'` it scanned, so it took the bound value into account. Don't rely on that: the PostgreSQL docs say matching happens at planning time and "parameterized query clauses do not work with a partial index". Write the predicate's literal (`status = 'pending'`) in the query, and bind only the other values.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('CREATE TABLE jobs (id INTEGER PRIMARY KEY, kind TEXT, status TEXT)')\nconn.execute(\"CREATE UNIQUE INDEX uq_jobs_running ON jobs (kind) WHERE status = 'running'\")\nresults = []\nfor kind, status in [('email', 'done'), ('email', 'done'), ('email', 'running'), ('email', 'running'), ('sms', 'running')]:\n    try:\n        conn.execute('INSERT INTO jobs (kind, status) VALUES (?, ?)', (kind, status))\n        results.append('ok')\n    except sqlite3.IntegrityError:\n        results.append('refused')\nprint(results)",
  "answer": "['ok', 'ok', 'ok', 'refused', 'ok']",
  "explanation": "Only 'running' rows are in the unique index. Done jobs can repeat; a second running email job can't; a running sms job is a different key." }
```

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "There's `CREATE INDEX ix_jobs_pending ON jobs (created_at) WHERE status = 'pending'`. The query `SELECT id FROM jobs WHERE status IN ('pending', 'retry') ORDER BY created_at LIMIT 10` scans the whole table. Why?",
  "options": ["The query's WHERE doesn't imply status = 'pending' (it also allows 'retry'), so the partial index can't be used", "Partial indexes can't be used with ORDER BY", "LIMIT disables indexes", "The index needs to be UNIQUE"], "answer": 0,
  "explanation": "A partial index only holds pending rows; a query that also wants retry rows can't be answered from it. Match the predicate exactly, or widen the index's WHERE." }
```

## 5. Your turn

Two things the messenger needs: **at most one pinned message per chat** (a partial unique index, plus a `pin_message` that now has to switch pins in the right order inside one transaction), and "who gets notifications" from a JSON settings column where a missing key means the default. Section 2's `coalesce` remark and section 4's predicate rule are the keys.

```exercise
DB.M08.L03.E1
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "For each, say column, JSON(B) or partial index, and why: (1) a message's sender, (2) per-user UI preferences that change every release, (3) 'a user has at most one default shipping address'.",
  "model": "(1) A column with a foreign key and NOT NULL: every message has one, and you filter and join on it. (2) JSON(B): sparse, varied and changing shape, read and written as a whole; keep it small. (3) A partial unique index on addresses(user_id) WHERE is_default: uniqueness only among default rows, which a plain UNIQUE can't express.",
  "explanation": "Columns for core, queried fields; JSON for variable blobs; partial indexes for rules or lookups over a subset of rows." }
```
