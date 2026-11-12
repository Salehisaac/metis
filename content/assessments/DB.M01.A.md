---
{ "id": "DB.M01.A", "module": "DB.M01", "title": "DB.M01 module assessment: SELECT, writes, grouping, date ranges", "minutes": 15 }
---
Answer without the lessons open, without running the code and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before DB.M02. If you came here from the placement check, this assessment plus the DB.M01.L03 exercise is your evidence for skipping the module.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE m(id INTEGER PRIMARY KEY, chat_id INTEGER, sender_id INTEGER, body TEXT, sent_at TEXT);\nINSERT INTO m(chat_id, sender_id, body, sent_at) VALUES (1,1,'a','2026-11-01 08:00:00'),(1,2,'b','2026-11-01 09:00:00'),(1,1,'  ','2026-11-02 10:00:00'),(2,1,'c','2026-11-02 11:00:00'),(1,3,'d','2026-11-03 00:00:00');''')\nprint(c.execute(\"SELECT sender_id, count(*) AS n FROM m WHERE chat_id = 1 AND sent_at >= '2026-11-01' AND sent_at < '2026-11-03' GROUP BY sender_id ORDER BY n DESC, sender_id\").fetchall())",
  "answer": "[(1, 2), (2, 1)]",
  "explanation": "Chat 1 only, and before Nov 3 (so sender 3's midnight message is out). Sender 1 has 2 rows (the blank one counts, since nothing filters it), sender 2 has 1. The chat 2 row is filtered by WHERE." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.executescript('''CREATE TABLE u(id INTEGER PRIMARY KEY, name TEXT, deleted_at TEXT);\nINSERT INTO u(name, deleted_at) VALUES ('ana', NULL), ('ben', '2026-11-01'), ('cy', NULL);''')\nprint(c.execute('SELECT count(*) FROM u WHERE deleted_at = NULL').fetchone()[0], c.execute('SELECT count(*) FROM u WHERE deleted_at IS NULL').fetchone()[0])",
  "answer": "0 2",
  "explanation": "`= NULL` is never true, so it matches nothing. IS NULL matches the two rows without a deleted_at." }
```

```quiz
{ "id": "a3", "type": "choice",
  "prompt": "`DELETE FROM chat_members WHERE chat_id = ? OR user_id = ?` is meant to remove one user from one chat. What does it actually do?",
  "options": ["Exactly that", "Removes everyone from that chat and that user from every chat", "Raises an error because of the OR", "Removes nothing"], "answer": 1,
  "explanation": "A row matches if either condition holds. Leaving one chat needs both: AND." }
```

```quiz
{ "id": "a4", "type": "output",
  "prompt": "No row has chat_id 9. What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE m(id INTEGER PRIMARY KEY, chat_id INTEGER, sender_id INTEGER, sent_at TEXT)')\nc.execute(\"INSERT INTO m(chat_id, sender_id, sent_at) VALUES (1, 1, '2026-11-01 08:00:00')\")\nprint(c.execute('SELECT count(*), sum(sender_id), max(sent_at) FROM m WHERE chat_id = 9').fetchone())",
  "answer": "(0, None, None)",
  "explanation": "An aggregate query without GROUP BY always returns one row. On zero rows count is 0, but sum and max are NULL (None)." }
```

```quiz
{ "id": "a5", "type": "truefalse",
  "prompt": "`SELECT id FROM messages WHERE chat_id = ? LIMIT 20` returns the chat's first 20 messages, oldest first.", "answer": false,
  "explanation": "Without ORDER BY the order is undefined, so you get some 20 messages. Use ORDER BY sent_at, id." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "A report counts messages per day with `WHERE sent_at BETWEEN '2026-11-01' AND '2026-11-07'`. A colleague says the Nov 7 numbers look too low. Explain the cause and the fix.",
  "model": "Times are text like '2026-11-07 14:00:00', which is greater than '2026-11-07', so BETWEEN (>= low AND <= high) drops every message on Nov 7 after midnight. Use a half-open range: sent_at >= '2026-11-01' AND sent_at < '2026-11-08'.",
  "explanation": "Half-open ranges include the start and exclude the first moment you don't want." }
```
