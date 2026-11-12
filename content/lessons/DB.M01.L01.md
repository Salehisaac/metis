---
{
  "id": "DB.M01.L01",
  "title": "Placement check, then SELECT: WHERE, ORDER BY, LIMIT",
  "difficulty": "beginner",
  "minutes": 60,
  "prerequisites": ["PY.M04"],
  "objectives": [
    "Take a 5-minute placement check and decide from its result whether to work through DB.M01 or skip ahead",
    "Run SQL from Python with sqlite3.connect, execute, fetchall and fetchone, and predict the Python values they return",
    "Filter rows with WHERE, using parentheses where AND/OR precedence matters and IS NULL for missing values",
    "Make result order fully defined with ORDER BY plus a tie-break, and take a page with LIMIT/OFFSET"
  ],
  "why": "Your assessment recorded basic SELECT as self-reported only, and the written SQL task was skipped, so nothing has measured it yet. This lesson measures it first, then fills the gaps that bite most often in real queries: NULL comparisons, AND/OR precedence and undefined row order.",
  "applications": [
    "The 'latest N messages in a chat' query behind every chat screen",
    "Admin and support queries: 'which messages from this user were never edited?'",
    "Page-by-page listings in an API (LIMIT/OFFSET)"
  ],
  "exercises": ["DB.M01.L01.E1"],
  "sources": [
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3, SQLite library 3.45.1)",
      "verified": "2026-11-12",
      "claims": ["connect(':memory:') opens an in-memory database", "Rows are returned as tuples by default (row_factory is None)", "Always use placeholders instead of string formatting to bind values", "For the qmark style, parameters must be a sequence matching the number of placeholders"]
    },
    {
      "title": "SQLite: SELECT",
      "url": "https://www.sqlite.org/lang_select.html",
      "version": "SQLite docs (current); behaviour checked locally on SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["Without ORDER BY, the order of a multi-row result is undefined", "Ties on all ORDER BY expressions come back in undefined order", "ASC is the default; NULLs are smaller than any other value when sorting", "LIMIT is an upper bound; OFFSET skips the first M rows; fewer rows than LIMIT is not an error", "A negative LIMIT means no upper bound"]
    },
    {
      "title": "SQLite: SQL Language Expressions",
      "url": "https://www.sqlite.org/lang_expr.html",
      "version": "SQLite docs (current); behaviour checked locally on SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["AND has higher precedence than OR", "Operators generally evaluate to NULL when any operand is NULL", "IS and IS NOT never evaluate to NULL", "x BETWEEN y AND z is x>=y AND x<=z"]
    }
  ]
}
---
## 0. Placement check (about 5 minutes)

DB.M01 is marked **REVIEW (provisional)**: you said you can write basic SELECT, INSERT and UPDATE, but the written SQL task in the assessment was skipped, so that claim has no evidence yet. Answer the six questions below **without running anything, without AI, and without the lessons open**. Only your first answer counts.

**What the result means**

- **All six right on the first try:** skip the teaching in this module. Write the exercise in DB.M01.L03 (the grouped, date-filtered query from the assessment) with no hints, then take the DB.M01 module assessment. If both pass, tell the mentor; DB.M01 can then be recorded as SKIP and you start DB.M02.
- **Anything wrong:** work through the module in order. It's about 4 hours. Each explanation below names the lesson that teaches that point.

Every question uses Python's built-in `sqlite3` module; section 1 explains the calls if they're new.

```quiz
{ "id": "p1", "type": "output", "label": "Placement",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE posts(id INTEGER PRIMARY KEY, author TEXT, likes INTEGER);\nINSERT INTO posts VALUES (1,'kim',5),(2,'lee',9),(3,'kim',9),(4,'park',2),(5,'lee',7);''')\nprint(c.execute('SELECT id FROM posts WHERE likes > 4 ORDER BY likes DESC, id LIMIT 3').fetchall())",
  "answer": "[(2,), (3,), (5,)]",
  "explanation": "Rows 1, 2, 3 and 5 pass the WHERE. Sorted by likes descending: 2 and 3 (9 likes, tie broken by id ascending), then 5 (7), then 1 (5). LIMIT 3 keeps the first three. Each row is a tuple, even with one column. Taught in DB.M01.L01." }
```

```quiz
{ "id": "p2", "type": "output", "label": "Placement",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE t(id INTEGER PRIMARY KEY, tag TEXT);\nINSERT INTO t(tag) VALUES ('a'), (NULL), ('b'), (NULL);''')\nprint(c.execute('SELECT count(*), count(tag) FROM t').fetchone())",
  "answer": "(4, 2)",
  "explanation": "count(*) counts rows; count(tag) counts rows where tag is not NULL. Taught in DB.M01.L03." }
```

```quiz
{ "id": "p3", "type": "output", "label": "Placement",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE p(author TEXT, likes INTEGER);\nINSERT INTO p VALUES ('kim',5),('lee',9),('kim',9),('park',2),('lee',7),('park',1);''')\nprint(c.execute('SELECT author, sum(likes) FROM p GROUP BY author HAVING sum(likes) > 10 ORDER BY author').fetchall())",
  "answer": "[('kim', 14), ('lee', 16)]",
  "explanation": "GROUP BY makes one group per author (kim 14, lee 16, park 3); HAVING drops the groups whose sum is 10 or less. Taught in DB.M01.L03." }
```

```quiz
{ "id": "p4", "type": "truefalse", "label": "Placement",
  "prompt": "`SELECT id FROM orders WHERE shipped_at = NULL` returns the orders that haven't shipped (shipped_at is NULL).", "answer": false,
  "explanation": "Comparing anything with NULL using = gives NULL, not true, so WHERE keeps no rows. You need `shipped_at IS NULL`. Taught in DB.M01.L01, section 3." }
```

```quiz
{ "id": "p5", "type": "choice", "label": "Placement",
  "prompt": "You want only the chats that have more than 100 messages, counted per chat. Which clause holds the condition `count(*) > 100`?",
  "options": ["WHERE", "HAVING", "ORDER BY", "LIMIT"], "answer": 1,
  "explanation": "WHERE filters single rows before grouping, so it can't see count(*). HAVING filters whole groups after they're aggregated. Taught in DB.M01.L03." }
```

```quiz
{ "id": "p6", "type": "output", "label": "Placement",
  "prompt": "The table p has 6 rows. What does this print? (`rowcount` is the number of rows the statement changed.)",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE p(author TEXT, likes INTEGER);\nINSERT INTO p VALUES ('kim',5),('lee',9),('kim',9),('park',2),('lee',7),('park',1);''')\nprint(c.execute('UPDATE p SET likes = 0').rowcount)",
  "answer": "6",
  "explanation": "An UPDATE without WHERE changes every row in the table. Taught in DB.M01.L02." }
```

## 1. Running SQL from Python

All DB modules run on **SQLite** through Python's built-in `sqlite3` module. SQLite is a library, not a server: the whole database is one file, or lives only in memory with `":memory:"`. That makes it perfect for exercises and tests: every test can start from a fresh database in a millisecond. Your day job uses MySQL; the SQL in DB.M01 and DB.M02 is the same in both, and the places where they differ are called out.

```python
import sqlite3

conn = sqlite3.connect(":memory:")       # Go: sql.Open(...)
conn.executescript("""
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, total INTEGER, shipped_at TEXT);
INSERT INTO orders VALUES
  (1, 'kim', 120, '2026-11-01'),
  (2, 'lee', 40,  NULL),
  (3, 'kim', 75,  '2026-11-03'),
  (4, 'park', 300, NULL),
  (5, 'lee', 75,  '2026-11-02');
""")

rows = conn.execute("SELECT id, customer, total FROM orders WHERE total >= 75").fetchall()
print(rows)
print(conn.execute("SELECT count(*) FROM orders").fetchone())
print(conn.execute("SELECT id FROM orders WHERE customer = ?", ("nobody",)).fetchone())
```

```text
[(1, 'kim', 120), (3, 'kim', 75), (4, 'park', 300), (5, 'lee', 75)]
(5,)
None
```

- `conn.execute(sql, params)` runs one statement and returns a cursor. Think of it as Go's `db.Query(query, args...)`.
- `.fetchall()` returns a **list of tuples**, one tuple per row. You don't need `rows.Next()` and `Scan`.
- `.fetchone()` returns **one tuple**, or `None` when there's no row. A one-column row is still a tuple: `(5,)`.
- `executescript` runs several statements at once. It takes no parameters, so use it only for fixed setup SQL like the block above.

**The `?` is a placeholder.** The value travels separately from the SQL text, the same way `db.Query("... WHERE id = ?", id)` works in Go. Never build SQL with f-strings or `+`. In the assessment you proposed escaping quotes by hand; DB.M04 shows exactly why that fails. For now, the rule is: **values only ever go in through `?`**.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE langs(id INTEGER PRIMARY KEY, name TEXT);\nINSERT INTO langs(name) VALUES ('go'), ('python');''')\nprint(c.execute('SELECT name FROM langs WHERE id = ?', (2,)).fetchone())\nprint(c.execute('SELECT name FROM langs WHERE id = ?', (9,)).fetchone())",
  "answer": "('python',)\nNone",
  "explanation": "fetchone returns a tuple per row, even for one column, and None when no row matches. The parameters are a tuple too: (2,) with the comma." }
```

## 2. WHERE: AND binds tighter than OR

WHERE keeps the rows for which the condition is **true**. Conditions combine with AND, OR and NOT, and **AND binds tighter than OR**, just like `&&` and `||` in Go. That's a classic source of bugs:

```python
# "kim or lee, and only big orders"
print(conn.execute("SELECT id FROM orders WHERE customer = 'kim' OR customer = 'lee' AND total > 100").fetchall())
print(conn.execute("SELECT id FROM orders WHERE (customer = 'kim' OR customer = 'lee') AND total > 100").fetchall())
```

```text
[(1,), (3,)]
[(1,)]
```

The first query is read as `customer = 'kim' OR (customer = 'lee' AND total > 100)`, so kim's 75 order (id 3) slips in. Add the parentheses, or use `customer IN ('kim', 'lee')`, which has no precedence trap.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE tickets(id INTEGER PRIMARY KEY, team TEXT, open INTEGER);\nINSERT INTO tickets VALUES (1,'api',1),(2,'web',0),(3,'api',0),(4,'web',1);''')\nprint(c.execute('SELECT id FROM tickets WHERE open = 1 AND team = ? OR team = ? ORDER BY id', ('api', 'web')).fetchall())",
  "answer": "[(1,), (2,), (4,)]",
  "explanation": "It's read as (open = 1 AND team = 'api') OR team = 'web'. That's ticket 1, plus every web ticket, open or not (2 and 4)." }
```

## 3. NULL is not a value you can compare

NULL means "unknown". Any comparison with NULL (`=`, `!=`, `<`) gives NULL, not true or false, and WHERE drops rows whose condition isn't true. Use `IS NULL` and `IS NOT NULL`: they always give true or false.

```python
print(conn.execute("SELECT id FROM orders WHERE shipped_at = NULL").fetchall())
print(conn.execute("SELECT id FROM orders WHERE shipped_at IS NULL").fetchall())
print(conn.execute("SELECT id FROM orders WHERE shipped_at != '2026-11-01'").fetchall())
```

```text
[]
[(2,), (4,)]
[(3,), (5,)]
```

The third query surprises most people: "not shipped on Nov 1" also *excludes* the unshipped orders 2 and 4, because `NULL != '2026-11-01'` is NULL. If you mean "including unshipped", say so: `shipped_at != '2026-11-01' OR shipped_at IS NULL`. Go has no equivalent, because `sql.NullString` makes you handle the missing value explicitly in code.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "`WHERE NOT (shipped_at = '2026-11-01')` returns the orders where shipped_at is NULL.", "answer": false,
  "explanation": "For a NULL shipped_at, the comparison is NULL, and NOT NULL is still NULL. The row is dropped. Only IS NULL / IS NOT NULL turn a missing value into true or false." }
```

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY, bio TEXT);\nINSERT INTO users VALUES (1,'hi'),(2,NULL),(3,''),(4,NULL);''')\nprint(c.execute('SELECT count(*) FROM users WHERE bio IS NULL').fetchone()[0], c.execute('SELECT count(*) FROM users WHERE bio <> ?', ('hi',)).fetchone()[0])",
  "answer": "2 1",
  "explanation": "Two rows have NULL. `bio <> 'hi'` is true only for the empty string (id 3); for the NULL rows it's NULL, so they don't count. An empty string is a value, not NULL." }
```

## 4. ORDER BY: no ORDER BY means no order

Without ORDER BY, the order of rows is **undefined**. The SQLite docs say so explicitly. Today's result often looks like insertion order, but that's an accident of how the table was scanned. An index or a new SQLite version can change it. It's the same idea as Go's map iteration order: never rely on it.

```python
print(conn.execute("SELECT id, total FROM orders ORDER BY total DESC, id").fetchall())
print(conn.execute("SELECT id, shipped_at FROM orders ORDER BY shipped_at").fetchall())
```

```text
[(4, 300), (1, 120), (3, 75), (5, 75), (2, 40)]
[(2, None), (4, None), (1, '2026-11-01'), (5, '2026-11-02'), (3, '2026-11-03')]
```

- Sorting is by the first key, then the second key breaks ties. Rows equal on *every* key come back in undefined order, so add a unique column (usually `id`) as the last key whenever order matters. Orders 3 and 5 both have 75; `id` decides.
- ASC (smallest first) is the default; DESC reverses it, and applies to one key only. `ORDER BY total DESC, id` is "total descending, then id ascending".
- SQLite sorts NULL as **smaller than every value**, so NULLs come first in ASC and last in DESC. Write `ASC NULLS LAST` or `DESC NULLS FIRST` to change that. Other databases don't all agree on where NULLs go, so be explicit when it matters.

The tie-break is the same lesson as the `sort.Slice` tie-break you skipped in the assessment's I1: a sort key that isn't unique gives you a nondeterministic order.

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "A chat screen shows `SELECT id, body FROM messages WHERE chat_id = ? ORDER BY sent_at DESC LIMIT 50`. Two messages often share the same sent_at second. What's the risk?",
  "options": ["None: SQLite always returns ties by id", "Tied messages can swap places between requests, and with paging one can be shown twice or skipped", "The query fails when two rows have the same sent_at", "LIMIT ignores tied rows"], "answer": 1,
  "explanation": "Ties come back in undefined order. Add `, id DESC` so the order is fully defined." }
```

## 5. LIMIT and OFFSET

`LIMIT n` is an upper bound on the number of rows; `OFFSET m` skips the first m rows of the sorted result. Asking for more rows than exist, or skipping past the end, is not an error:

```python
print(conn.execute("SELECT id FROM orders ORDER BY id LIMIT 2 OFFSET 2").fetchall())
print(conn.execute("SELECT id FROM orders ORDER BY id LIMIT 2 OFFSET 10").fetchall())
```

```text
[(3,), (4,)]
[]
```

LIMIT is applied **after** ORDER BY, so "the 3 most recent" is `ORDER BY time DESC LIMIT 3`. LIMIT without ORDER BY gives you *some* 3 rows, not the first 3. LIMIT and OFFSET values can be `?` placeholders too.

```quiz
{ "id": "q6", "type": "output",
  "prompt": "Pages have 2 rows. What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE tags(name TEXT);\nINSERT INTO tags VALUES ('sql'),('go'),('py'),('api'),('db');''')\npage = 3\nprint(c.execute('SELECT name FROM tags ORDER BY name LIMIT ? OFFSET ?', (2, (page - 1) * 2)).fetchall())",
  "answer": "[('sql',)]",
  "explanation": "Sorted: api, db, go, py, sql. Page 3 skips 4 rows and gets at most 2, but only 'sql' is left." }
```

## 6. Your turn

The exercise uses the messaging schema that all four DB modules share: `users`, `chats`, `chat_members` and `messages`. Open `chatdb.py` in the exercise folder and read the `messages` rows before you write anything. Times are text like `'2026-11-09 08:00:00'`, which sorts correctly as text.

Write each query, then run pytest. When a test fails, run your query by hand in a Python REPL (`import chatdb; conn = chatdb.make_db()`) and compare its rows with the expected ones.

```exercise
DB.M01.L01.E1
```
