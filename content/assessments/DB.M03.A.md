---
{ "id": "DB.M03.A", "module": "DB.M03", "title": "DB.M03 module assessment: transactions and atomicity", "minutes": 15 }
---
Answer without the lessons open, without running the code and without AI. Only your **first** answer counts. This module exists because of one assessment answer ("a crash between two DELETEs leaves both done"), so the mentor will look at a1 and a6 closely. If you miss more than one, ask for practice before DB.M04.

```quiz
{ "id": "a1", "type": "choice",
  "prompt": "A script runs `DELETE FROM messages WHERE chat_id = 7` and then `DELETE FROM chats WHERE id = 7` on a connection in SQLite's autocommit mode (no BEGIN). The machine loses power between the two. What's in the database afterwards?",
  "options": ["Both deletes are done", "Neither delete is done", "The messages are gone and chat 7 still exists", "The database file is corrupted"], "answer": 2,
  "explanation": "In autocommit mode each statement is its own transaction, committed when it finishes. The second statement never ran. Inside one BEGIN ... COMMIT, neither would be done." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE t(x INTEGER NOT NULL)')\ntry:\n    with c:\n        c.execute('INSERT INTO t VALUES (1)')\n        c.execute('INSERT INTO t VALUES (2)')\n        c.execute('INSERT INTO t VALUES (NULL)')\nexcept sqlite3.IntegrityError:\n    pass\nwith c:\n    c.execute('INSERT INTO t VALUES (3)')\nprint(c.execute('SELECT x FROM t ORDER BY x').fetchall())",
  "answer": "[(3,)]",
  "explanation": "The first block raised, so it rolled back 1 and 2 as well. The second block committed 3." }
```

```quiz
{ "id": "a3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:', autocommit=True)\nc.execute('CREATE TABLE t(x INTEGER NOT NULL)')\ntry:\n    with c:\n        c.execute('INSERT INTO t VALUES (1)')\n        c.execute('INSERT INTO t VALUES (NULL)')\nexcept sqlite3.IntegrityError:\n    pass\nprint(c.execute('SELECT count(*) FROM t').fetchone()[0])",
  "answer": "1",
  "explanation": "With autocommit=True, every statement commits on its own and `with conn:` does nothing. Multi-step writes in this mode need an explicit BEGIN and COMMIT." }
```

```quiz
{ "id": "a4", "type": "truefalse",
  "prompt": "In Python's default sqlite3 mode, `conn.close()` commits any pending changes before closing.", "answer": false,
  "explanation": "close() doesn't commit; pending changes are lost. Commit (or leave a `with conn:` block normally) before closing." }
```

```quiz
{ "id": "a5", "type": "choice",
  "prompt": "A function does INSERT, INSERT, then raises ValueError without any rollback and without `with conn:`. Which test assertion detects the bug?",
  "options": ["A second connection sees no new rows", "pytest.raises(ValueError)", "The caller's connection still sees the two rows, and conn.in_transaction is True", "The function returns None"], "answer": 2,
  "explanation": "The rows were never committed, so a second connection can't see them either way, and the error is raised correctly. Only the caller's connection shows the pending rows that the next commit would keep." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Your Go service deletes a chat with two db.Exec calls (members, then chat) against MySQL with default settings. Describe what can go wrong and how you'd change the code.",
  "model": "MySQL starts connections with autocommit on, so each Exec is its own committed transaction. If the process dies or the second Exec fails, the members are deleted but the chat remains: half an operation. Wrap both in one transaction: tx, err := db.Begin(); defer tx.Rollback(); tx.Exec(...); tx.Exec(...); return tx.Commit(). Then a failure or crash before Commit leaves both in place. A test should make the second step fail and check that the members are still there.",
  "explanation": "Atomicity comes from one transaction around all the steps, plus a test that proves the rollback." }
```
