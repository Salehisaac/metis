---
{
  "id": "DB.M02.L03",
  "title": "LEFT JOIN, NULLs and missing rows",
  "difficulty": "intermediate",
  "minutes": 60,
  "prerequisites": ["DB.M02.L02"],
  "objectives": [
    "Predict the rows of a LEFT JOIN, including the NULL-filled row for each unmatched left row",
    "Count matches correctly after a LEFT JOIN with count(right.column) instead of count(*)",
    "Decide whether a condition on the right-hand table belongs in ON or in WHERE, and explain how WHERE can turn a LEFT JOIN into an INNER JOIN",
    "Find rows with no match (anti-join) with LEFT JOIN ... IS NULL or NOT EXISTS, and avoid the NOT IN NULL trap"
  ],
  "why": "Reports usually need the zeros: users who never wrote, chats with no activity this week. An INNER JOIN silently drops them, and the classic LEFT JOIN mistakes (count(*) and a condition in WHERE) bring the wrong numbers back without any error. These are the bugs that make dashboards lie.",
  "applications": [
    "'Messages per user', including users with 0",
    "Finding members who never posted, or tags no post uses",
    "Activity reports that list every chat, even the quiet ones"
  ],
  "exercises": ["DB.M02.L03.E1"],
  "sources": [
    {
      "title": "SQLite: SELECT",
      "url": "https://www.sqlite.org/lang_select.html",
      "version": "SQLite docs (current); behaviour checked locally on SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["LEFT JOIN: after the ON filtering, an extra row is added for each left row that matches no right row, with NULL in the right-hand columns", "RIGHT JOIN and FULL JOIN are supported and mirror or combine the LEFT JOIN rule"]
    },
    {
      "title": "SQLite: Built-in Aggregate Functions",
      "url": "https://www.sqlite.org/lang_aggfunc.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["count(X) counts non-NULL X; count(*) counts all rows", "sum() of no non-NULL values is NULL"]
    },
    {
      "title": "SQLite: SQL Language Expressions",
      "url": "https://www.sqlite.org/lang_expr.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["NOT IN gives NULL when the right side contains NULL and the left value isn't found", "EXISTS always evaluates to 0 or 1", "coalesce() returns its first non-NULL argument"]
    }
  ]
}
---
## 1. LEFT JOIN keeps the left side

Same blog data as last lesson. park has no posts, so an INNER JOIN drops park. A **LEFT JOIN** runs the ON filter exactly like an INNER JOIN, and then **adds one row for each left row that matched nothing**, with NULL in every right-hand column:

```python
print(conn.execute("""
SELECT a.name, p.title
FROM authors AS a
LEFT JOIN posts AS p ON p.author_id = a.id
ORDER BY a.id, p.id
""").fetchall())
```

```text
[('kim', 'Go to Python'), ('kim', 'SQLite tips'), ('lee', 'Hello'), ('park', None)]
```

Row count rule: **matches, plus one per unmatched left row**. kim 2 + lee 1 + park's extra row = 4. "Left" means the table written before `LEFT JOIN`, so put the table whose rows must all appear first. (SQLite also has RIGHT JOIN and FULL JOIN; RIGHT JOIN is just LEFT JOIN with the tables swapped, so most people write LEFT JOIN only.)

In Go you'd get `sql.NullString` for `p.title` on park's row; in Python, `None`. Use `coalesce(p.title, '(none)')` to show a default instead.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE teams(id INTEGER PRIMARY KEY, name TEXT);\nCREATE TABLE players(id INTEGER PRIMARY KEY, team_id INTEGER, name TEXT);\nINSERT INTO teams VALUES (1, 'red'), (2, 'blue'), (3, 'green');\nINSERT INTO players VALUES (1, 1, 'a'), (2, 1, 'b'), (3, 2, 'c');''')\nprint(c.execute('SELECT t.name, p.name FROM teams AS t LEFT JOIN players AS p ON p.team_id = t.id ORDER BY t.id, p.id').fetchall())",
  "answer": "[('red', 'a'), ('red', 'b'), ('blue', 'c'), ('green', None)]",
  "explanation": "red matches two players, blue one, and green none, so green gets one extra row with NULL (None) for the player." }
```

## 2. Counting after a LEFT JOIN: count(column), not count(*)

```python
print(conn.execute("""
SELECT a.name, count(*) AS wrong, count(p.id) AS posts
FROM authors AS a
LEFT JOIN posts AS p ON p.author_id = a.id
GROUP BY a.id, a.name
ORDER BY a.id
""").fetchall())
```

```text
[('kim', 2, 2), ('lee', 1, 1), ('park', 1, 0)]
```

park's group contains one row, the NULL-filled one, so `count(*)` says 1. `count(p.id)` counts non-NULL values, so it says 0. **After a LEFT JOIN, count a column of the right table**, preferably its primary key, which is never NULL in a real match. The same applies to `sum`: on park's row it gives NULL, not 0, unless you write `coalesce(sum(...), 0)`.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);\nCREATE TABLE orders(id INTEGER PRIMARY KEY, user_id INTEGER, total INTEGER);\nINSERT INTO users VALUES (1,'ana'),(2,'ben'),(3,'cy');\nINSERT INTO orders(user_id,total) VALUES (1,10),(1,5),(3,7);''')\nprint(c.execute('SELECT u.name, count(*), count(o.id), sum(o.total) FROM users AS u LEFT JOIN orders AS o ON o.user_id = u.id GROUP BY u.id, u.name ORDER BY u.id').fetchall())",
  "answer": "[('ana', 2, 2, 15), ('ben', 1, 0, None), ('cy', 1, 1, 7)]",
  "explanation": "ben has no orders: one NULL row, so count(*) is 1, count(o.id) is 0 and sum is NULL (None)." }
```

## 3. ON or WHERE? The silent INNER JOIN

"Every author, with how many of their posts start with S":

```python
print(conn.execute("""
SELECT a.name, count(p.id)
FROM authors AS a
LEFT JOIN posts AS p ON p.author_id = a.id
WHERE p.title LIKE 'S%'
GROUP BY a.id, a.name
ORDER BY a.id
""").fetchall())
print(conn.execute("""
SELECT a.name, count(p.id)
FROM authors AS a
LEFT JOIN posts AS p ON p.author_id = a.id AND p.title LIKE 'S%'
GROUP BY a.id, a.name
ORDER BY a.id
""").fetchall())
```

```text
[('kim', 1)]
[('kim', 1), ('lee', 0), ('park', 0)]
```

The first query lost lee and park. WHERE runs **after** the join. On park's NULL row, `p.title LIKE 'S%'` is NULL, so WHERE drops it; lee's only row ('Hello') fails too. The LEFT JOIN has been turned into an INNER JOIN, and nothing warns you.

The rule:

- A condition that decides **which right-hand rows count as a match** goes in **ON**. Unmatched left rows still survive.
- A condition that decides **which left-hand rows appear at all** goes in **WHERE**.

A WHERE condition on a right-hand column almost always means you wanted an INNER JOIN, unless it's `IS NULL` (next section).

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "`SELECT c.id, count(m.id) FROM chats AS c LEFT JOIN messages AS m ON m.chat_id = c.id WHERE m.sender_id = ? GROUP BY c.id` is meant to list every chat with the number of messages from one user. What goes wrong?",
  "options": ["Nothing", "Chats where that user never wrote disappear, because WHERE removes their NULL rows", "count(m.id) counts every message, not just the user's", "It fails: WHERE can't refer to m after a LEFT JOIN"], "answer": 1,
  "explanation": "Move `m.sender_id = ?` into the ON clause; then chats without that user's messages keep their NULL row and show 0." }
```

## 4. Finding what's missing: the anti-join

"Which tags does no post use?" Keep the LEFT JOIN's unmatched rows, and only those:

```python
print(conn.execute("""
SELECT t.name
FROM tags AS t
LEFT JOIN post_tags AS pt ON pt.tag_id = t.id
WHERE pt.tag_id IS NULL
ORDER BY t.name
""").fetchall())
print(conn.execute("""
SELECT t.name
FROM tags AS t
WHERE NOT EXISTS (SELECT 1 FROM post_tags AS pt WHERE pt.tag_id = t.id)
ORDER BY t.name
""").fetchall())
```

```text
[('rust',)]
[('rust',)]
```

Here the IS NULL test belongs in WHERE: it runs after the join and keeps exactly the rows the LEFT JOIN added. Test a column that can't be NULL in a real match (a key column). `NOT EXISTS` says the same thing in words: "tags for which no post_tags row exists". Both are fine; pick the one you can read.

**Avoid `NOT IN` with a subquery that can return NULL:**

```python
conn.execute("CREATE TABLE drafts (id INTEGER PRIMARY KEY, author_id INTEGER)")
conn.execute("INSERT INTO drafts (author_id) VALUES (1), (NULL)")
print(conn.execute("SELECT name FROM authors WHERE id NOT IN (SELECT author_id FROM drafts)").fetchall())
```

```text
[]
```

"Authors without drafts" should be lee and park, but one NULL in the subquery makes `id NOT IN (...)` NULL for every author who isn't found (SQL can't be sure 2 isn't the unknown value), so no row is returned. NOT EXISTS and the LEFT JOIN version don't have this trap.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);\nCREATE TABLE logins(user_id INTEGER, at TEXT);\nINSERT INTO users VALUES (1,'ana'),(2,'ben'),(3,'cy');\nINSERT INTO logins VALUES (1,'2026-11-01'),(1,'2026-11-05'),(3,'2026-10-01');''')\nprint(c.execute('SELECT u.name FROM users AS u LEFT JOIN logins AS l ON l.user_id = u.id AND l.at >= ? WHERE l.user_id IS NULL ORDER BY u.name', ('2026-11-01',)).fetchall())",
  "answer": "[('ben',), ('cy',)]",
  "explanation": "The date is in ON, so cy's October login doesn't count as a match. ben has no logins at all. Both get the NULL row, and WHERE keeps exactly those: users with no login since Nov 1." }
```

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "`WHERE id NOT IN (SELECT user_id FROM bans)` returns no rows at all if bans contains a single row whose user_id is NULL.", "answer": true,
  "explanation": "For any id not found in the list, NOT IN against a list containing NULL is NULL, not true. Use NOT EXISTS or a LEFT JOIN ... IS NULL." }
```

## 5. Your turn

Three queries where the rows without a match are the point. For each, first write down which users or chats should appear with 0 or be found as "silent", using the data in `chatdb.py`. Then write the query and compare.

```exercise
DB.M02.L03.E1
```
