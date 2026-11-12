---
{
  "id": "DB.M02.L04",
  "title": "Joining three tables: fan-out and one row per group",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["DB.M02.L03"],
  "objectives": [
    "Predict the row count when one table is joined to two one-to-many children, and explain why counts and sums get multiplied (fan-out)",
    "Compute several per-group numbers without fan-out, using correlated subqueries or pre-aggregated derived tables",
    "Return the whole 'latest row per group' with a correlated subquery that has a fully defined order, instead of max() plus bare columns",
    "Choose between count(DISTINCT), subqueries and window functions for a given query and justify the choice"
  ],
  "why": "Real screens combine several relationships at once: a chat list shows members, message counts and the last message. Joining everything in one FROM is the natural first attempt, and it returns numbers that are too big without any error. The 'latest message per chat' query is asked in almost every backend interview, and the bare-column shortcut from DB.M01.L03 gets it wrong.",
  "applications": [
    "A messenger's chat list: members, message count, last activity per chat",
    "The latest message, order or login per user or chat",
    "Dashboards that show several counts per row"
  ],
  "exercises": ["DB.M02.L04.E1"],
  "sources": [
    {
      "title": "SQLite: SELECT",
      "url": "https://www.sqlite.org/lang_select.html",
      "version": "SQLite docs (current); behaviour checked locally on SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["Joins of more than two tables are processed left to right", "A bare column with a single max() takes its value from a row holding the max, but ties are resolved arbitrarily", "NULLs sort as smallest; DESC NULLS FIRST / ASC NULLS LAST change that"]
    },
    {
      "title": "SQLite: SQL Language Expressions",
      "url": "https://www.sqlite.org/lang_expr.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["Scalar and correlated subqueries can be used as expressions"]
    },
    {
      "title": "SQLite: Window Functions",
      "url": "https://www.sqlite.org/windowfunctions.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["Window function support was added in SQLite 3.25.0", "row_number() numbers rows within a partition according to the window's ORDER BY"]
    }
  ]
}
---
## 1. Fan-out: two children multiply

This lesson's blog has authors, posts with a publication time, and comments on posts:

```text
authors:  (1, 'kim'), (2, 'lee'), (3, 'park')
posts:    (10, kim, 'Go to Python', 2026-11-01 09:00), (11, kim, 'SQLite tips', 2026-11-03 09:00), (12, lee, 'Hello', 2026-11-02 09:00)
comments: post 10 has 3, post 11 has 1, post 12 has 1
```

"Per author: how many posts, how many comments?" The first attempt joins everything:

```python
print(conn.execute("""
SELECT a.name, count(p.id) AS posts, count(c.id) AS comments
FROM authors AS a
LEFT JOIN posts AS p ON p.author_id = a.id
LEFT JOIN comments AS c ON c.post_id = p.id
GROUP BY a.id, a.name
ORDER BY a.id
""").fetchall())
```

```text
[('kim', 4, 4), ('lee', 1, 1), ('park', 0, 0)]
```

kim has 2 posts, not 4. Look at kim's rows before grouping:

```python
print(conn.execute("""
SELECT a.name, p.id, c.id
FROM authors AS a
LEFT JOIN posts AS p ON p.author_id = a.id
LEFT JOIN comments AS c ON c.post_id = p.id
WHERE a.id = 1
ORDER BY p.id, c.id
""").fetchall())
```

```text
[('kim', 10, 1), ('kim', 10, 2), ('kim', 10, 3), ('kim', 11, 4)]
```

Post 10 appears **once per comment**. Joining down a chain of one-to-many relationships repeats every parent row once per child, so `count(p.id)` counts post 10 three times. This is **fan-out**. It gets worse when a table has two *independent* children, like a chat with members and messages: each chat produces members × messages rows, and every count and sum is multiplied.

**Debugging habit:** when a number looks too big, remove the GROUP BY and look at the raw joined rows for one group, as above.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "Chat 1 has 3 members and 4 messages. How many rows does the join produce for chat 1?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE chats(id INTEGER PRIMARY KEY);\nCREATE TABLE members(chat_id INTEGER, user_id INTEGER);\nCREATE TABLE msgs(id INTEGER PRIMARY KEY, chat_id INTEGER);\nINSERT INTO chats VALUES (1);\nINSERT INTO members VALUES (1, 1), (1, 2), (1, 3);\nINSERT INTO msgs(chat_id) VALUES (1), (1), (1), (1);''')\nprint(c.execute('SELECT count(*) FROM chats AS ch JOIN members AS mb ON mb.chat_id = ch.id JOIN msgs AS m ON m.chat_id = ch.id').fetchone()[0])",
  "answer": "12",
  "explanation": "Each member row pairs with each message row of the same chat: 3 × 4 = 12. Any count over this join is inflated." }
```

## 2. Fixing fan-out: compute each number on its own

**Option A: a correlated subquery per number.** A subquery in the SELECT list that refers to the outer row (`a.id`) runs once per outer row and returns one value:

```python
print(conn.execute("""
SELECT a.name,
       (SELECT count(*) FROM posts AS p WHERE p.author_id = a.id) AS posts,
       (SELECT count(*) FROM comments AS c JOIN posts AS p ON p.id = c.post_id
         WHERE p.author_id = a.id) AS comments
FROM authors AS a
ORDER BY a.id
""").fetchall())
```

```text
[('kim', 2, 4), ('lee', 1, 1), ('park', 0, 0)]
```

The outer query has exactly one row per author and joins nothing, so nothing multiplies. Inside a subquery `count(*)` is fine: it only sees matching rows, and returns 0 when there are none.

**Option B: `count(DISTINCT ...)`** on the fanned-out join:

```python
print(conn.execute("""
SELECT a.name, count(DISTINCT p.id) AS posts, count(c.id) AS comments
FROM authors AS a
LEFT JOIN posts AS p ON p.author_id = a.id
LEFT JOIN comments AS c ON c.post_id = p.id
GROUP BY a.id, a.name
ORDER BY a.id
""").fetchall())
```

```text
[('kim', 2, 4), ('lee', 1, 1), ('park', 0, 0)]
```

Same numbers, but it's a patch: the database still builds the multiplied rows, and DISTINCT can't fix a `sum()`, because two posts with the same value are not duplicates. Use it for counting distinct keys, not as a general fan-out fix.

**Option C: pre-aggregate**, then join: `LEFT JOIN (SELECT author_id, count(*) AS n FROM posts GROUP BY author_id) AS ps ON ps.author_id = a.id`. The derived table has one row per author, so joining it can't fan out. On large tables this is often the fastest of the three.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "Per customer you need the number of orders and the sum of all payments. Orders and payments are both children of customers. Which approach gives correct numbers?",
  "options": ["Join customers, orders and payments, then count(DISTINCT o.id) and sum(DISTINCT p.amount)", "Join all three, then count(o.id) and sum(p.amount)", "Compute the order count and the payment sum in separate subqueries (correlated or pre-aggregated) per customer", "Join all three and divide the sum by the order count"], "answer": 2,
  "explanation": "The three-way join multiplies rows. sum(DISTINCT) would also merge two different payments of the same amount. Compute each number separately." }
```

## 3. The latest row per group

"Each author's newest post, with its title." `max(published_at)` gives the newest **value**, but the title would be a bare column. SQLite happens to take it from the max row, *unless two rows tie*, and then the choice is arbitrary. Pick the row explicitly with a correlated subquery that has a fully defined order:

```python
print(conn.execute("""
SELECT a.name, p.title, p.published_at
FROM authors AS a
JOIN posts AS p ON p.author_id = a.id
WHERE p.id = (SELECT p2.id FROM posts AS p2
              WHERE p2.author_id = a.id
              ORDER BY p2.published_at DESC, p2.id DESC
              LIMIT 1)
ORDER BY a.id
""").fetchall())
```

```text
[('kim', 'SQLite tips', '2026-11-03 09:00:00'), ('lee', 'Hello', '2026-11-02 09:00:00')]
```

For each post, the subquery finds the id of its author's newest post (with `id DESC` deciding ties), and the WHERE keeps the post only if it's that one. park has no posts, so the INNER JOIN leaves park out. Use a LEFT JOIN with the condition moved into ON if park must appear with NULLs.

The modern alternative is a **window function** (SQLite has them since 3.25.0):

```python
print(conn.execute("""
SELECT name, title, published_at FROM (
  SELECT a.name, p.title, p.published_at,
         row_number() OVER (PARTITION BY a.id ORDER BY p.published_at DESC, p.id DESC) AS rn
  FROM authors AS a JOIN posts AS p ON p.author_id = a.id
) WHERE rn = 1 ORDER BY name
""").fetchall())
```

```text
[('kim', 'SQLite tips', '2026-11-03 09:00:00'), ('lee', 'Hello', '2026-11-02 09:00:00')]
```

`row_number()` numbers each author's posts 1, 2, 3... in the given order, and the outer query keeps number 1. Both versions are correct; the window function reads better once you're used to it, and makes "top 3 per group" a one-character change (`rn <= 3`).

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "`SELECT chat_id, id, max(sent_at) FROM messages GROUP BY chat_id` always returns the id of each chat's newest message in SQLite.", "answer": false,
  "explanation": "With a single max(), SQLite takes bare columns from a row holding the max, but if two messages share the newest sent_at, which one is arbitrary. Other databases reject the query. Use a subquery with ORDER BY sent_at DESC, id DESC LIMIT 1, or row_number()." }
```

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE logins(id INTEGER PRIMARY KEY, user_id INTEGER, at TEXT);\nINSERT INTO logins(user_id, at) VALUES (1,'2026-11-01'),(2,'2026-11-03'),(1,'2026-11-04'),(2,'2026-11-03'),(3,'2026-10-30');''')\nprint(c.execute('SELECT l.user_id, l.id FROM logins AS l WHERE l.id = (SELECT x.id FROM logins AS x WHERE x.user_id = l.user_id ORDER BY x.at DESC, x.id DESC LIMIT 1) ORDER BY l.user_id').fetchall())",
  "answer": "[(1, 3), (2, 4), (3, 5)]",
  "explanation": "User 1's newest login is id 3 (Nov 4). User 2 has two logins on Nov 3 (ids 2 and 4); id DESC picks 4. User 3 has one login, id 5." }
```

## 4. Ordering by a value that may be missing

A chat list sorts by last activity, and a chat without messages has none (NULL). SQLite sorts NULL as the smallest value, so in a DESC sort NULLs already come last. Write `DESC NULLS LAST` anyway: it states the intent, and not every database puts NULLs in the same place.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE chats(id INTEGER PRIMARY KEY, last_at TEXT);\nINSERT INTO chats VALUES (1, '2026-11-02'), (2, NULL), (3, '2026-11-05'), (4, '2026-11-02');''')\nprint(c.execute('SELECT id FROM chats ORDER BY last_at DESC NULLS LAST, id').fetchall())",
  "answer": "[(3,), (1,), (4,), (2,)]",
  "explanation": "Newest first (3), then the tie on Nov 2 broken by id (1, 4), and the chat without activity last." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "A teammate's dashboard query joins users to orders and to support_tickets, then shows count(o.id) and count(t.id) per user. A user with 3 orders and 2 tickets shows 6 and 6. Explain the cause in one or two sentences and propose a fix.",
  "model": "Fan-out: orders and tickets are independent children of users, so the join pairs every order with every ticket (3 × 2 = 6 rows) and both counts count those rows. Compute each count separately: correlated subqueries per user, or join pre-aggregated (SELECT user_id, count(*) ... GROUP BY user_id) tables.",
  "explanation": "Two independent one-to-many joins multiply." }
```

## 5. Your turn

The exercise is the home screen of the messenger: the chat list for a user, and the newest message per chat. Before writing CHAT_LIST, write down from `chatdb.py` what you expect for user 1: three chats, with how many members and messages each. If your first attempt shows bigger numbers, remove the GROUP BY and look at the raw rows for chat 1.

```exercise
DB.M02.L04.E1
```
