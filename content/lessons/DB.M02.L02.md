---
{
  "id": "DB.M02.L02",
  "title": "INNER JOIN and counting result rows",
  "difficulty": "intermediate",
  "minutes": 60,
  "prerequisites": ["DB.M02.L01"],
  "objectives": [
    "Explain an INNER JOIN as 'all pairs of rows, filtered by the ON condition', and predict the number of result rows from the data",
    "Join along a foreign key with table aliases, and fix an 'ambiguous column name' error",
    "Join through a junction table to follow a many-to-many relationship",
    "Join a table to itself to compare two rows of the same table"
  ],
  "why": "You told us JOINs are where SQL gets hard for you. The usual reason is guessing the result instead of being able to predict it. One mental model, pairs of rows filtered by ON, predicts every INNER JOIN result, including the row count, which is how you catch duplicated rows before they reach a report.",
  "applications": [
    "Showing usernames next to messages instead of sender ids",
    "Listing a chat's members, or a user's chats, through chat_members",
    "Finding the chats two users have in common (a self-join)"
  ],
  "exercises": ["DB.M02.L02.E1"],
  "sources": [
    {
      "title": "SQLite: SELECT",
      "url": "https://www.sqlite.org/lang_select.html",
      "version": "SQLite docs (current); behaviour checked locally on SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["All joins are based on the cartesian product: Nleft x Nright rows", "Without ON or USING, JOIN, INNER JOIN, CROSS JOIN and comma give the cartesian product", "The ON expression is evaluated for each row of the cartesian product, and only rows where it is true are kept", "INNER JOIN, JOIN and the comma operator are interchangeable in SQLite", "More than two tables are joined left to right"]
    }
  ]
}
---
## 1. The mental model: pairs, then a filter

Examples use a small blog database (the schema from DB.M02.L01, plus a third author and a fourth tag):

```text
authors: (1, 'kim'), (2, 'lee'), (3, 'park')
posts:   (10, author 1, 'Go to Python'), (11, author 1, 'SQLite tips'), (12, author 2, 'Hello')
tags:    (1, 'python'), (2, 'sql'), (3, 'go'), (4, 'rust')
post_tags (post_id, tag_id): (10, 1), (10, 3), (11, 2), (11, 1)
```

A join starts from **every pair** of a row on the left with a row on the right: the cartesian product. 3 authors × 3 posts is 9 pairs:

```python
print(conn.execute("SELECT count(*) FROM authors, posts").fetchone())
```

```text
(9,)
```

The ON condition then keeps only the pairs where it's **true**:

```python
rows = conn.execute("""
SELECT p.id, p.title, a.name
FROM posts AS p
JOIN authors AS a ON a.id = p.author_id
ORDER BY p.id
""").fetchall()
print(rows)
```

```text
[(10, 'Go to Python', 'kim'), (11, 'SQLite tips', 'kim'), (12, 'Hello', 'lee')]
```

Of the 9 pairs, only 3 have `a.id = p.author_id`. That's the whole model; the database is free to compute it far more cleverly, but the result is always "pairs where ON is true". In Go terms, it's the nested loop `for p in posts { for a in authors { if a.ID == p.AuthorID { emit(p, a) } } }`.

**Predicting the row count.** Following a foreign key from the "many" side to the "one" side (post → its author) gives **exactly one row per post**: each post matches one author. park has no posts, so park appears in no pair that survives. An INNER JOIN drops rows that have no match; the next lesson keeps them.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE teams(id INTEGER PRIMARY KEY, name TEXT);\nCREATE TABLE players(id INTEGER PRIMARY KEY, team_id INTEGER, name TEXT);\nINSERT INTO teams VALUES (1, 'red'), (2, 'blue'), (3, 'green');\nINSERT INTO players VALUES (1, 1, 'a'), (2, 1, 'b'), (3, 2, 'c'), (4, NULL, 'd');''')\nprint(c.execute('SELECT count(*) FROM teams, players').fetchone()[0], c.execute('SELECT count(*) FROM players AS p JOIN teams AS t ON t.id = p.team_id').fetchone()[0])",
  "answer": "12 3",
  "explanation": "Without ON: 3 × 4 = 12 pairs. With ON: one row per player that has a matching team. Player d has team_id NULL, and NULL = anything is not true, so d is dropped." }
```

## 2. Aliases, and the ambiguous column

`FROM posts AS p` gives the table a short name; then `p.title` says which table a column comes from. Once two joined tables share a column name, you **must** qualify it:

```python
try:
    conn.execute("SELECT id, name FROM posts JOIN authors ON authors.id = posts.author_id")
except Exception as e:
    print(type(e).__name__ + ":", e)
```

```text
OperationalError: ambiguous column name: id
```

Both tables have `id`. Qualify every column in a join query (`p.id`, `a.name`), even the ones that happen to be unique today; tomorrow someone adds a `name` column to posts.

**Filtering works as usual.** WHERE runs on the joined rows, so you can filter by a column of either table. "Posts by kim" is a filter on the author's name, not a hard-coded id:

```python
print(conn.execute("""
SELECT a.name, p.title
FROM authors AS a
JOIN posts AS p ON p.author_id = a.id
WHERE a.name = ?
ORDER BY p.id
""", ("kim",)).fetchall())
```

```text
[('kim', 'Go to Python'), ('kim', 'SQLite tips')]
```

Notice that `'kim'` appears twice: from the author's side, a one-to-many join **repeats the "one" row** once per matching child. That's correct here, and it's exactly what causes double counting in DB.M02.L04.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "`SELECT id, username, body FROM messages JOIN users ON users.id = messages.sender_id` fails with 'ambiguous column name: id'. Best fix?",
  "options": ["Rename users.id to user_id", "Use aliases and qualify every column: `SELECT m.id, u.username, m.body FROM messages AS m JOIN users AS u ON u.id = m.sender_id`", "Remove id from the SELECT", "Use a comma join instead of JOIN"], "answer": 1,
  "explanation": "Both tables have an id column, so the database can't guess. Qualify it, and the others too." }
```

## 3. Many-to-many: two joins through the junction table

To list posts with their tags, go post → post_tags → tag. The joins run left to right: the first JOIN produces a result, and the second joins *that* to the next table.

```python
print(conn.execute("""
SELECT p.title, t.name
FROM posts AS p
JOIN post_tags AS pt ON pt.post_id = p.id
JOIN tags AS t ON t.id = pt.tag_id
ORDER BY p.id, t.name
""").fetchall())
```

```text
[('Go to Python', 'go'), ('Go to Python', 'python'), ('SQLite tips', 'python'), ('SQLite tips', 'sql')]
```

The row count is **the number of post_tags rows** (4), because each junction row matches exactly one post and one tag. Post 12 has no tags and the tag 'rust' has no posts, so neither appears.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);\nCREATE TABLE groups_(id INTEGER PRIMARY KEY, name TEXT);\nCREATE TABLE members(group_id INTEGER, user_id INTEGER, PRIMARY KEY (group_id, user_id));\nINSERT INTO users VALUES (1,'ana'), (2,'ben'), (3,'cy');\nINSERT INTO groups_ VALUES (1,'ops'), (2,'dev');\nINSERT INTO members VALUES (1,1), (2,1), (2,2);''')\nprint(c.execute('SELECT g.name, u.name FROM members AS m JOIN users AS u ON u.id = m.user_id JOIN groups_ AS g ON g.id = m.group_id ORDER BY g.name, u.name').fetchall())",
  "answer": "[('dev', 'ana'), ('dev', 'ben'), ('ops', 'ana')]",
  "explanation": "One row per members row (3). cy is in no group, so cy doesn't appear." }
```

## 4. Joining a table to itself

Which posts have **both** tag 1 (python) and tag 2 (sql)? One post_tags row can only hold one tag, so you need two rows of the same table side by side. Give the table two aliases and join it to itself:

```python
print(conn.execute("""
SELECT x.post_id
FROM post_tags AS x
JOIN post_tags AS y ON y.post_id = x.post_id
WHERE x.tag_id = ? AND y.tag_id = ?
ORDER BY x.post_id
""", (1, 2)).fetchall())
```

```text
[(11,)]
```

Each output row pairs two tag rows of the same post. Only post 11 has a pair with python on one side and sql on the other. A common mistake is `WHERE tag_id = 1 AND tag_id = 2` on one copy of the table: one row can't have two values in one column, so it returns nothing.

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "`SELECT post_id FROM post_tags WHERE tag_id = 1 AND tag_id = 2` returns the posts that have both tags.", "answer": false,
  "explanation": "Each row has a single tag_id, which can't equal 1 and 2 at once, so no row matches. You need two rows at a time: a self-join (or GROUP BY post_id HAVING count(*) = 2 with WHERE tag_id IN (1, 2))." }
```

## 5. Old-style comma joins

You'll see `FROM posts p, authors a WHERE a.id = p.author_id` in older code. In SQLite, `,`, `JOIN` and `INNER JOIN` are interchangeable, so it gives the same rows. Prefer `JOIN ... ON`: the join condition sits next to the table it belongs to, and forgetting it is obvious. With the comma style, a forgotten condition silently becomes a cartesian product, the 9-pair table from section 1.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "A colleague forgot the ON condition. How many rows does this count?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE chats(id INTEGER PRIMARY KEY);\nCREATE TABLE msgs(id INTEGER PRIMARY KEY, chat_id INTEGER);\nINSERT INTO chats VALUES (1), (2), (3);\nINSERT INTO msgs(chat_id) VALUES (1), (1), (2), (2), (2);''')\nprint(c.execute('SELECT count(*) FROM msgs JOIN chats').fetchone()[0])",
  "answer": "15",
  "explanation": "No ON: every message paired with every chat, 5 × 3 = 15. With ON chats.id = msgs.chat_id it would be 5." }
```

## 6. Your turn

Four queries on the messaging data. Before you write each one, predict the number of rows from the data in `chatdb.py`, then check your result against that number. If you get more rows than you expected, look at the ON condition first.

```exercise
DB.M02.L02.E1
```
