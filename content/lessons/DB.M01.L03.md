---
{
  "id": "DB.M01.L03",
  "title": "Aggregates: COUNT, GROUP BY, HAVING and date ranges",
  "difficulty": "beginner",
  "minutes": 60,
  "prerequisites": ["DB.M01.L01"],
  "objectives": [
    "Predict the results of count(*), count(col), count(DISTINCT col), sum and max on data with NULLs and on zero rows",
    "Write GROUP BY queries and put each condition in the right clause: WHERE for rows, HAVING for groups",
    "Recognise a bare column in a grouped query and explain why its value is arbitrary",
    "Filter a time range with a half-open interval (>= start, < end) on ISO text times, and group by day with date()",
    "Pass values with named placeholders (:name) and a dict"
  ],
  "why": "This is the query you skipped in the assessment: 'top senders in a period'. Reports, dashboards, rate limits and leaderboards are all GROUP BY queries. The two classic bugs, a condition in the wrong clause and an off-by-one date range, both return plausible numbers, so nobody notices.",
  "applications": [
    "Top senders, most active chats, messages per day",
    "Rate limiting: 'more than 20 messages in the last minute?'",
    "Daily reports with a time range that doesn't double-count midnight"
  ],
  "exercises": ["DB.M01.L03.E1"],
  "sources": [
    {
      "title": "SQLite: SELECT",
      "url": "https://www.sqlite.org/lang_select.html",
      "version": "SQLite docs (current); behaviour checked locally on SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["Rows with equal GROUP BY values form one group; NULLs are considered equal for grouping", "HAVING is evaluated once per group and discards groups where it is false", "An aggregate query without GROUP BY returns exactly one row, even with zero input rows", "A bare column takes its value from an arbitrary row of the group; with a single min() or max() it comes from the row with that value", "Most other SQL engines disallow bare columns"]
    },
    {
      "title": "SQLite: Built-in Aggregate Functions",
      "url": "https://www.sqlite.org/lang_aggfunc.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["count(X) counts non-NULL X; count(*) counts all rows in the group", "sum() returns NULL when there are no non-NULL input rows", "count(DISTINCT X) counts distinct values"]
    },
    {
      "title": "SQLite: Date And Time Functions",
      "url": "https://www.sqlite.org/lang_datefunc.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["SQLite has no dedicated date/time type; ISO-8601 text is one supported storage format", "date() returns YYYY-MM-DD; datetime() returns YYYY-MM-DD HH:MM:SS", "Modifiers 'NNN days' and 'start of day'"]
    },
    {
      "title": "SQLite: SQL Language Expressions",
      "url": "https://www.sqlite.org/lang_expr.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["x BETWEEN y AND z is equivalent to x>=y AND x<=z", "Named parameters :AAAA"]
    },
    {
      "title": "SQLite: Built-In Scalar SQL Functions",
      "url": "https://www.sqlite.org/lang_corefunc.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["trim(X) removes spaces from both ends of X"]
    },
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Named style placeholders take a dict containing a key for every named parameter", "Using named placeholders with a sequence emits DeprecationWarning in 3.12"]
    }
  ]
}
---
## 1. Aggregates: many rows in, one value out

Examples in this lesson use this table:

```python
import sqlite3

conn = sqlite3.connect(":memory:")
conn.executescript("""
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, total INTEGER, coupon TEXT, placed_at TEXT);
INSERT INTO orders (customer, total, coupon, placed_at) VALUES
  ('kim',  120, 'FALL', '2026-10-30 22:15:00'),
  ('lee',   40, NULL,   '2026-10-31 09:00:00'),
  ('kim',   75, NULL,   '2026-10-31 23:59:00'),
  ('park', 300, 'FALL', '2026-11-01 00:00:00'),
  ('lee',   75, 'VIP',  '2026-11-01 13:30:00'),
  ('kim',   20, NULL,   '2026-11-02 08:00:00');
""")
print(conn.execute("SELECT count(*), count(coupon), count(DISTINCT coupon), sum(total), max(total) FROM orders").fetchone())
print(conn.execute("SELECT count(*), sum(total) FROM orders WHERE customer = 'nobody'").fetchone())
```

```text
(6, 3, 2, 630, 300)
(0, None)
```

- `count(*)` counts **rows**. `count(coupon)` counts rows where coupon **is not NULL**. `count(DISTINCT coupon)` counts different non-NULL values (FALL, VIP).
- An aggregate query without GROUP BY always returns **exactly one row**, even when no rows match. On zero rows `count` gives 0 but `sum` gives **NULL** (`None`), not 0. Code that does `total + 10` on that result crashes with a `TypeError`. Use `coalesce(sum(total), 0)` when you want 0.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE m(id INTEGER PRIMARY KEY, sender TEXT, edited_at TEXT);\nINSERT INTO m(sender, edited_at) VALUES ('ana', NULL), ('ben', '2026-11-02'), ('ana', '2026-11-03'), ('ana', NULL);''')\nprint(c.execute('SELECT count(*), count(edited_at), count(DISTINCT sender) FROM m').fetchone())",
  "answer": "(4, 2, 2)",
  "explanation": "4 rows; 2 have a non-NULL edited_at; 2 different senders (ana, ben)." }
```

## 2. GROUP BY: one result row per group

GROUP BY splits the rows into groups with equal values, and each aggregate is computed **per group**. In Go you'd write a loop with `totals[o.Customer] += o.Total`. GROUP BY is that loop, run inside the database.

```python
print(conn.execute("""
SELECT customer, count(*) AS orders, sum(total) AS spent
FROM orders
GROUP BY customer
ORDER BY spent DESC
""").fetchall())
```

```text
[('park', 1, 300), ('kim', 3, 215), ('lee', 2, 115)]
```

`AS spent` names the output column, and ORDER BY can use that name. The groups come out in no particular order unless you sort them.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE m(id INTEGER PRIMARY KEY, chat_id INTEGER, sender TEXT);\nINSERT INTO m(chat_id, sender) VALUES (1,'ana'),(1,'ben'),(2,'ana'),(1,'ana'),(3,'cy');''')\nprint(c.execute('SELECT chat_id, count(*) FROM m GROUP BY chat_id ORDER BY count(*) DESC, chat_id').fetchall())",
  "answer": "[(1, 3), (2, 1), (3, 1)]",
  "explanation": "Chat 1 has 3 rows. Chats 2 and 3 tie at 1, and the second sort key puts 2 first." }
```

## 3. WHERE filters rows, HAVING filters groups

The clauses run in this order: **FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT**. WHERE throws away single rows *before* any grouping, so it can't use `count(*)`. HAVING throws away whole groups *after* they're aggregated.

```python
# customers with at least 2 orders of 50 or more
print(conn.execute("""
SELECT customer, count(*) AS orders
FROM orders
WHERE total >= 50
GROUP BY customer
HAVING count(*) >= 2
ORDER BY customer
""").fetchall())
```

```text
[('kim', 2)]
```

kim has 3 orders, but the WHERE removed the 20 one before counting. lee has 2 orders, but only one of them is 50 or more. Moving `total >= 50` into HAVING would change the meaning (and in SQLite it would use an arbitrary row's total, see the next section). Rule of thumb: **a condition about one row goes in WHERE; a condition about a count, sum or other aggregate goes in HAVING.**

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "Rate limit: find senders with more than 20 messages since a given time. Which query is right?",
  "options": [
    "SELECT sender_id FROM messages WHERE sent_at >= ? AND count(*) > 20 GROUP BY sender_id",
    "SELECT sender_id FROM messages WHERE sent_at >= ? GROUP BY sender_id HAVING count(*) > 20",
    "SELECT sender_id FROM messages GROUP BY sender_id HAVING count(*) > 20",
    "SELECT sender_id, count(*) FROM messages WHERE sent_at >= ? ORDER BY count(*) DESC LIMIT 20"
  ], "answer": 1,
  "explanation": "The time filter is about rows (WHERE); the count is about groups (HAVING). The first is an error (an aggregate in WHERE), the third ignores the time window, and the fourth returns one aggregated row, not a list of senders." }
```

## 4. Bare columns: a value from an arbitrary row

What should this return for `total`? kim has three orders.

```python
print(conn.execute("SELECT customer, total, count(*) FROM orders GROUP BY customer ORDER BY customer").fetchall())
```

```text
[('kim', 120, 3), ('lee', 40, 2), ('park', 300, 1)]
```

`total` is neither grouped nor aggregated: SQLite calls it a **bare column** and takes its value from **an arbitrary row of the group**. 120 here, but nothing guarantees which. Most other databases reject this query with an error, and the SQLite docs call bare columns an SQLite-specific extension. One documented special case: with exactly one `min()` or `max()`, bare columns come from the row that has the min or max. Don't build on it; it isn't portable. **Every selected column should be in GROUP BY or inside an aggregate.**

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "In SQLite, `SELECT chat_id, body, count(*) FROM messages GROUP BY chat_id` returns each chat's most recent message as body.", "answer": false,
  "explanation": "body is a bare column, so its value comes from an arbitrary row of each group. 'Most recent message per chat' needs a different query (DB.M02.L04)." }
```

## 5. Dates are text: use half-open ranges

SQLite has no date type. The schema stores times as ISO text, `'2026-11-01 13:30:00'`, which sorts and compares correctly **as text** as long as every value has the same format (and the same time zone; ours are UTC). MySQL has real `DATETIME` columns, but the range logic below is the same.

The classic bug is `BETWEEN` with dates:

```python
print(conn.execute("SELECT id FROM orders WHERE placed_at BETWEEN '2026-10-31' AND '2026-11-01' ORDER BY id").fetchall())
print(conn.execute("SELECT id FROM orders WHERE placed_at >= ? AND placed_at < ? ORDER BY id", ("2026-10-31", "2026-11-02")).fetchall())
print(conn.execute("SELECT '2026-11-01 00:00:00' > '2026-11-01'").fetchone())
```

```text
[(2,), (3,)]
[(2,), (3,), (4,), (5,)]
(1,)
```

"Orders on Oct 31 and Nov 1" with BETWEEN lost both Nov 1 orders. BETWEEN means `>= low AND <= high`, and as text, `'2026-11-01 00:00:00'` is *greater* than `'2026-11-01'` (it's longer and starts the same). The fix is a **half-open range**: `>= start AND < end`, with `end` the first moment you *don't* want. Back-to-back ranges then never overlap and never leave gaps: [Oct 31, Nov 2) and [Nov 2, Nov 3) share no row.

To report **per day**, group by `date(...)`, which cuts the time off:

```python
print(conn.execute("""
SELECT date(placed_at) AS day, count(*) AS orders, sum(total) AS revenue
FROM orders
GROUP BY day
ORDER BY day
""").fetchall())
print(conn.execute("SELECT date('2026-11-01 13:30:00'), date('2026-11-01', '+7 days'), datetime('2026-11-01 13:30:00', 'start of day')").fetchone())
```

```text
[('2026-10-30', 1, 120), ('2026-10-31', 2, 115), ('2026-11-01', 2, 375), ('2026-11-02', 1, 20)]
('2026-11-01', '2026-11-08', '2026-11-01 00:00:00')
```

```quiz
{"id": "q5", "type": "output", "prompt": "You want the logins on Nov 7 and Nov 8. What does this print?", "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE logins(id INTEGER PRIMARY KEY, at TEXT);\nINSERT INTO logins(at) VALUES ('2026-11-06 23:59:59'), ('2026-11-07 00:00:00'), ('2026-11-07 18:00:00'), ('2026-11-08 00:00:00'), ('2026-11-08 09:30:00');''')\nprint(c.execute('SELECT count(*) FROM logins WHERE at BETWEEN ? AND ?', ('2026-11-07', '2026-11-08')).fetchone()[0], c.execute('SELECT count(*) FROM logins WHERE at >= ? AND at < ?', ('2026-11-07', '2026-11-09')).fetchone()[0])", "answer": "2 4", "explanation": "BETWEEN '2026-11-07' AND '2026-11-08' stops at the text '2026-11-08', and both Nov 8 logins are greater than that, so only the two Nov 7 logins count. The half-open range [Nov 7, Nov 9) gets all four, and the Nov 6 login is excluded either way."}
```

## 6. Named placeholders

With four values, `?` placeholders get hard to read and easy to reorder by mistake. sqlite3 also accepts **named** placeholders, `:name`, with a dict:

```python
print(conn.execute("SELECT customer, sum(total) FROM orders WHERE placed_at >= :since GROUP BY customer ORDER BY customer", {"since": "2026-11-01"}).fetchall())
```

```text
[('kim', 20), ('lee', 75), ('park', 300)]
```

The dict must contain every name used in the SQL; extra keys are ignored. Passing a tuple to a query with named placeholders is deprecated in Python 3.12 (a `DeprecationWarning`), and the docs say it becomes an error in 3.14. DB.M04 covers placeholders in depth.

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE m(id INTEGER PRIMARY KEY, chat_id INTEGER, sent_at TEXT);\nINSERT INTO m(chat_id, sent_at) VALUES (1,'2026-11-01 10:00:00'),(1,'2026-11-01 11:00:00'),(1,'2026-11-02 09:00:00'),(2,'2026-11-01 12:00:00');''')\nprint(c.execute('SELECT date(sent_at) AS day, count(*) FROM m WHERE chat_id = :chat GROUP BY day HAVING count(*) >= :min ORDER BY day', {'chat': 1, 'min': 2}).fetchall())",
  "answer": "[('2026-11-01', 2)]",
  "explanation": "Chat 1 has 2 messages on Nov 1 and 1 on Nov 2; HAVING keeps days with at least 2. Chat 2's message is filtered out by WHERE before grouping." }
```

## 7. Your turn

This is the assessment's skipped SQL task, on the shared messaging data. If you came here straight from the placement check, write it **without hints**; that's the evidence that lets you skip ahead.

Look at the `messages` rows in `chatdb.py` first, especially message 7 (a body of only spaces) and the messages sent exactly at midnight and at `2026-11-09 08:00:00`. Those are the edge cases the tests check.

```exercise
DB.M01.L03.E1
```
