---
{ "id": "DB.M06.A", "module": "DB.M06", "title": "DB.M06 module assessment: locking and concurrency", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before moving on.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "Two connections, deferred transactions, both read before writing. What does this print?",
  "code": "import os, sqlite3, tempfile\npath = os.path.join(tempfile.mkdtemp(), 'a.db')\na = sqlite3.connect(path, isolation_level=None, timeout=0)\nb = sqlite3.connect(path, isolation_level=None, timeout=0)\na.execute('CREATE TABLE stock (id INTEGER PRIMARY KEY, qty INTEGER)')\na.execute('INSERT INTO stock VALUES (1, 5)')\na.execute('BEGIN')\nb.execute('BEGIN')\nqa = a.execute('SELECT qty FROM stock').fetchone()[0]\nqb = b.execute('SELECT qty FROM stock').fetchone()[0]\na.execute('UPDATE stock SET qty = ?', (qa - 1,))\ntry:\n    b.execute('UPDATE stock SET qty = ?', (qb - 1,))\n    print('b updated')\nexcept sqlite3.OperationalError as e:\n    print('b:', e)\nb.execute('ROLLBACK')\na.execute('COMMIT')\nprint(a.execute('SELECT qty FROM stock').fetchone()[0])",
  "answer": "b: database is locked\n4",
  "explanation": "a's UPDATE took the only RESERVED lock, so b can't upgrade its read transaction to a write. b rolls back, a commits 4. Inside transactions the lost update became an error instead; b must retry from the start." }
```

```quiz
{ "id": "a2", "type": "choice",
  "prompt": "Which statement about PostgreSQL's default isolation level is correct?",
  "options": ["It's Read Committed: each statement sees data committed before that statement started", "It's Serializable, so anomalies are impossible", "It's Read Uncommitted, so dirty reads happen", "It's Repeatable Read, like MySQL InnoDB"], "answer": 0,
  "explanation": "PostgreSQL defaults to Read Committed. MySQL InnoDB defaults to Repeatable Read; SQLite is serializable." }
```

```quiz
{ "id": "a3", "type": "choice", "label": "Debugging",
  "prompt": "`stock = SELECT qty ...; UPDATE products SET qty = ? WHERE id = ?` with `stock - n`. Under load, stock goes wrong. What's the best fix?",
  "options": ["UPDATE products SET qty = qty - ? WHERE id = ? AND qty >= ?, then check rowcount", "Add an index on products.id", "Increase the busy timeout", "Run the SELECT with a LIMIT"], "answer": 0,
  "explanation": "It's a lost update. One conditional UPDATE does the check and the arithmetic atomically, and rowcount reports whether there was enough stock." }
```

```quiz
{ "id": "a4", "type": "truefalse",
  "prompt": "In SQLite, a transaction started with plain `BEGIN` holds the write lock from that moment until COMMIT.", "answer": false,
  "explanation": "BEGIN (DEFERRED) takes no lock. Use BEGIN IMMEDIATE to take the write (RESERVED) lock at the start." }
```

```quiz
{ "id": "a5", "type": "output",
  "prompt": "Optimistic concurrency. What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:', isolation_level=None)\nconn.execute('CREATE TABLE notes (id INTEGER PRIMARY KEY, text TEXT, version INTEGER)')\nconn.execute(\"INSERT INTO notes VALUES (1, 'x', 4)\")\nsave = 'UPDATE notes SET text = ?, version = version + 1 WHERE id = ? AND version = ?'\nresults = [conn.execute(save, (t, 1, v)).rowcount for t, v in [('a', 4), ('b', 4), ('c', 5), ('d', 9)]]\nprint(results, conn.execute('SELECT text, version FROM notes').fetchone())",
  "answer": "[1, 0, 1, 0] ('c', 6)",
  "explanation": "'a' matches version 4 and makes it 5; 'b' is stale; 'c' matches 5 and makes it 6; 'd' claims a version that never existed." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "For each feature, pick atomic UPDATE, pessimistic lock or optimistic version, and say why in one line: (1) message view counter, (2) admins editing a group description, (3) a job queue where workers claim the oldest pending job.",
  "model": "(1) Atomic UPDATE views = views + 1: the change fits in one statement, no lock or version needed. (2) Optimistic version: the edit spans two requests with a human in between; detect conflicts and return 409. (3) Pessimistic: claim inside BEGIN IMMEDIATE (or SELECT ... FOR UPDATE in PostgreSQL), or one UPDATE ... WHERE id = (SELECT ...) statement; it's short and high-contention, so waiting briefly beats failing and retrying.",
  "explanation": "Use the cheapest tool that makes the read-modify-write atomic for the feature's shape." }
```
