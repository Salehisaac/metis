---
{ "id": "DB.M02.A", "module": "DB.M02", "title": "DB.M02 module assessment: relational modeling and JOINs", "minutes": 15 }
---
Answer without the lessons open, without running the code and without AI. Only your **first** answer counts. For the output questions, predict the row count first; that's the skill this module is about. If you miss more than one, ask the mentor for practice before DB.M03.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);\nCREATE TABLE msgs(id INTEGER PRIMARY KEY, sender_id INTEGER);\nINSERT INTO users VALUES (1,'ana'),(2,'ben'),(3,'cy');\nINSERT INTO msgs(sender_id) VALUES (1),(1),(1),(3);''')\nprint(c.execute('SELECT count(*) FROM users AS u JOIN msgs AS m ON m.sender_id = u.id').fetchone()[0], c.execute('SELECT count(*) FROM users AS u LEFT JOIN msgs AS m ON m.sender_id = u.id').fetchone()[0])",
  "answer": "4 5",
  "explanation": "INNER: one row per matching message (4). LEFT: the 4 matches plus one NULL row for ben, who has no messages." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);\nCREATE TABLE msgs(id INTEGER PRIMARY KEY, sender_id INTEGER);\nINSERT INTO users VALUES (1,'ana'),(2,'ben');\nINSERT INTO msgs(sender_id) VALUES (1),(1);''')\nprint(c.execute('SELECT u.name, count(*), count(m.id) FROM users AS u LEFT JOIN msgs AS m ON m.sender_id = u.id GROUP BY u.id, u.name ORDER BY u.id').fetchall())",
  "answer": "[('ana', 2, 2), ('ben', 1, 0)]",
  "explanation": "ben's group is a single NULL-filled row: count(*) counts it, count(m.id) doesn't." }
```

```quiz
{ "id": "a3", "type": "choice",
  "prompt": "`SELECT c.id, count(m.id) FROM chats AS c LEFT JOIN messages AS m ON m.chat_id = c.id WHERE m.sent_at >= ? GROUP BY c.id` should list every chat with its recent message count. What happens to chats with no recent messages?",
  "options": ["They appear with 0", "They disappear, because WHERE removes their NULL rows", "They appear with 1", "The query fails"], "answer": 1,
  "explanation": "The date condition must go in ON (`ON m.chat_id = c.id AND m.sent_at >= ?`) so chats without a match keep their row." }
```

```quiz
{ "id": "a4", "type": "output",
  "prompt": "Order 1 has 2 items and 3 shipments. What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE orders(id INTEGER PRIMARY KEY);\nCREATE TABLE items(id INTEGER PRIMARY KEY, order_id INTEGER, price INTEGER);\nCREATE TABLE shipments(id INTEGER PRIMARY KEY, order_id INTEGER);\nINSERT INTO orders VALUES (1);\nINSERT INTO items(order_id, price) VALUES (1, 10), (1, 5);\nINSERT INTO shipments(order_id) VALUES (1), (1), (1);''')\nprint(c.execute('SELECT count(i.id), sum(i.price) FROM orders AS o JOIN items AS i ON i.order_id = o.id JOIN shipments AS s ON s.order_id = o.id').fetchone())",
  "answer": "(6, 45)",
  "explanation": "Fan-out: 2 items × 3 shipments = 6 rows, and each price is counted three times: 3 × 15 = 45." }
```

```quiz
{ "id": "a5", "type": "truefalse",
  "prompt": "In SQLite, a REFERENCES clause in CREATE TABLE is enough for the database to reject a message whose chat_id doesn't exist.", "answer": false,
  "explanation": "Foreign keys are off by default in SQLite; each connection must run PRAGMA foreign_keys = ON." }
```

```quiz
{ "id": "a6", "type": "choice",
  "prompt": "Messages can be pinned in a chat by members, and the app must show who pinned each message and when. A message can be pinned by several members. Which design fits?",
  "options": ["A pinned_by TEXT column on messages with comma-separated user ids", "A pinned INTEGER flag on messages", "A pins table (message_id → messages, user_id → users, pinned_at) with primary key (message_id, user_id)", "A pinned_message_id column on users"], "answer": 2,
  "explanation": "It's many-to-many between messages and users, with a fact about each pair (pinned_at): a junction table with a composite key." }
```
