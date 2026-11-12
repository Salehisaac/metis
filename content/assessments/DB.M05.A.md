---
{ "id": "DB.M05.A", "module": "DB.M05", "title": "DB.M05 module assessment: indexes and query plans", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before DB.M06.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY, author_id INTEGER, published_at TEXT, title TEXT)')\nconn.execute('CREATE INDEX idx_posts_author_published ON posts (author_id, published_at)')\nsql = 'SELECT title FROM posts WHERE published_at > ? ORDER BY published_at'\nfor *_, detail in conn.execute('EXPLAIN QUERY PLAN ' + sql, ('2026-01-01',)):\n    print(detail)",
  "answer": "SCAN posts\nUSE TEMP B-TREE FOR ORDER BY",
  "explanation": "The index starts with author_id, which the query doesn't constrain, so it can't be searched on published_at. SQLite scans the table and sorts. An index starting with published_at would be needed." }
```

```quiz
{ "id": "a2", "type": "choice",
  "prompt": "Query: `SELECT id FROM tickets WHERE project_id = ? AND status = ? ORDER BY updated_at DESC LIMIT 20`. Which single index lets SQLite search and skip the sort step?",
  "options": ["(project_id, status, updated_at)", "(updated_at, project_id, status)", "(project_id, updated_at, status)", "(status) and (project_id) as two separate indexes"], "answer": 0,
  "explanation": "Both equality columns first, then the sort column. With updated_at first, nothing can be searched; with updated_at in the middle, status can't be searched (and the order breaks between statuses)." }
```

```quiz
{ "id": "a3", "type": "truefalse",
  "prompt": "If a table has indexes on `(a)` and `(a, b)`, dropping `(a)` makes searches on `a` alone fall back to a full scan.", "answer": false,
  "explanation": "(a) is a prefix of (a, b), so the longer index serves searches on a alone. The shorter one only costs writes." }
```

```quiz
{ "id": "a4", "type": "choice", "label": "Debugging",
  "prompt": "A plan shows `SEARCH users USING INDEX idx_users_country (country=?)`, but the query is no faster than without the index. 92% of users have country = 'IR'. What's the most likely explanation?",
  "options": ["The index matches most rows, so each match costs an index read plus a table lookup, which isn't cheaper than one scan", "The index is corrupt and needs REINDEX", "SEARCH plans are never faster than SCAN", "The query is using placeholders, which disables indexes"], "answer": 0,
  "explanation": "Indexes pay off when they narrow the rows to a small fraction (high selectivity). 'country = IR' selects most of the table." }
```

```quiz
{ "id": "a5", "type": "output",
  "prompt": "`timeit.repeat(run, repeat=4, number=50)` returned `[2.0, 1.5, 1.8, 1.6]`. What does this print?",
  "code": "rounds = [2.0, 1.5, 1.8, 1.6]\nprint(f'{min(rounds) / 50 * 1000:.0f} ms')",
  "answer": "30 ms",
  "explanation": "Take the fastest round, 1.5 s for 50 calls, which is 0.03 s, or 30 ms, per call." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Your team wants to add five indexes to `messages` before launch 'to be safe'. Describe how you'd decide which (if any) to add.",
  "model": "Start from the real hot queries, not columns. For each: check EXPLAIN QUERY PLAN; if it's a SCAN or a temp B-tree on a big table, design one composite index (equality columns, then the range/sort column, maybe covering columns). Seed realistic data, time the query before and after with timeit (min per call), and measure insert time with the index too, since messages is a hot write path. Keep only indexes that give a clear read win for a frequent query, and drop any that are prefixes of others.",
  "explanation": "Indexes are a trade-off: justify each one with a query, a plan and a measurement." }
```
