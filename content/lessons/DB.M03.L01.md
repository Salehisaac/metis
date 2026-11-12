---
{
  "id": "DB.M03.L01",
  "title": "Autocommit, crashes and atomic transactions",
  "difficulty": "intermediate",
  "minutes": 60,
  "prerequisites": ["DB.M02"],
  "objectives": [
    "Explain autocommit: every statement outside an explicit transaction is its own transaction, committed when it finishes",
    "Predict what a crash between two writes leaves behind, with and without an explicit transaction",
    "Group writes with BEGIN, COMMIT and ROLLBACK, and predict the state after each",
    "Explain that a failing statement is undone on its own while the transaction stays open, so the program must decide to roll back",
    "Describe in two sentences how SQLite's rollback journal makes a transaction atomic across a crash"
  ],
  "why": "In the assessment you answered that a crash between two DELETEs leaves 'both done anyway'. That's the one outcome that can't happen. What does happen depends on whether the two statements share a transaction, and getting that wrong is how half-deleted chats and half-done transfers end up in production. This lesson replaces the guess with a demonstration.",
  "applications": [
    "Deleting a chat and its messages, or moving money between accounts, as one unit",
    "Knowing what your Go code does today: two db.Exec calls under MySQL's default autocommit are two transactions",
    "Reasoning about deploys and crashes: which writes survive a kill -9"
  ],
  "exercises": [],
  "sources": [
    {
      "title": "SQLite: Transaction",
      "url": "https://www.sqlite.org/lang_transaction.html",
      "version": "SQLite docs (current); behaviour checked locally on SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["No reads or writes occur except within a transaction; a command starts one automatically if none is active, and it commits when the statement finishes", "BEGIN starts a transaction that lasts until COMMIT or ROLLBACK", "BEGIN inside a transaction fails with an error (transactions don't nest)", "END TRANSACTION is an alias for COMMIT"]
    },
    {
      "title": "SQLite: Atomic Commit In SQLite",
      "url": "https://www.sqlite.org/atomiccommit.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["Atomic commit: either all changes of a transaction occur or none do, even across an OS crash or power failure", "Original page content is written to a rollback journal before the database file is changed", "A hot journal left by a crash is played back by the next process that opens the database", "Deleting the rollback journal is the instant the transaction commits"]
    },
    {
      "title": "SQLite: ON CONFLICT clause",
      "url": "https://www.sqlite.org/lang_conflict.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["ABORT (the default) backs out the current statement; earlier changes in the same transaction are preserved and the transaction remains active"]
    },
    {
      "title": "MySQL 8.4 Reference Manual: autocommit, Commit, and Rollback",
      "url": "https://dev.mysql.com/doc/refman/8.4/en/innodb-autocommit-commit-rollback.html",
      "version": "MySQL 8.4 Reference Manual (not run here: no MySQL server on this machine)",
      "verified": "2026-11-12",
      "claims": ["Each new connection starts with autocommit enabled: each statement is its own transaction, committed if it didn't return an error", "START TRANSACTION or BEGIN ... COMMIT or ROLLBACK groups statements", "A session with autocommit disabled that ends without committing has its transaction rolled back"]
    },
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["autocommit=True selects SQLite's autocommit mode; commit() and rollback() then have no effect", "in_transaction reports whether a transaction is open"]
    }
  ]
}
---
## 1. Your assessment answer, revisited

The question: a program runs `DELETE FROM messages WHERE chat_id = 1` and then `DELETE FROM chats WHERE id = 1`, and crashes between the two. Your answer was "both done anyway".

The second DELETE **never ran**: the process died before reaching it. Nothing can do it later on the program's behalf. So "both done" is impossible. The two real outcomes are:

- **Only the first is done**, if each statement was its own transaction (autocommit). The chat still exists, with its messages gone.
- **Neither is done**, if both were inside one transaction that hadn't committed yet. The database rolls the first DELETE back.

Which one you get is decided by the code, not by luck. The rest of this lesson shows both, on a real crash.

## 2. Autocommit: every statement is its own transaction

SQLite never reads or writes outside a transaction. When you run a statement and no transaction is open, SQLite **starts one automatically and commits it as soon as the statement finishes**. That's autocommit mode. MySQL behaves the same way by default: each new connection starts with autocommit on, so each statement is committed on its own.

In Go terms: two `db.Exec` calls against MySQL are **two transactions**. Only `tx, _ := db.Begin()` followed by `tx.Exec(...)` and `tx.Commit()` makes them one.

To see SQLite's behaviour without Python adding anything, these examples connect with `autocommit=True` (Python's switch for SQLite's own autocommit mode; the next lesson covers all the options). Here's the crash, for real. The child process runs the first DELETE and then kills itself with `os._exit(1)`, which skips every cleanup, like a `kill -9` or a power cut:

```python
import os
import sqlite3
import subprocess
import sys

CHILD = """
import os, sqlite3, sys
conn = sqlite3.connect(sys.argv[1], autocommit=True)  # SQLite's own autocommit mode
if sys.argv[2] == "transaction":
    conn.execute("BEGIN")
conn.execute("DELETE FROM messages WHERE chat_id = 1")
os._exit(1)  # simulated crash: the process dies here, no cleanup at all
conn.execute("DELETE FROM chats WHERE id = 1")
if sys.argv[2] == "transaction":
    conn.execute("COMMIT")
"""

for mode in ["autocommit", "transaction"]:
    path = f"crash_{mode}.db"
    if os.path.exists(path):
        os.remove(path)
    setup = sqlite3.connect(path)
    setup.executescript("""
        CREATE TABLE chats (id INTEGER PRIMARY KEY, title TEXT);
        CREATE TABLE messages (id INTEGER PRIMARY KEY, chat_id INTEGER, body TEXT);
        INSERT INTO chats VALUES (1, 'team');
        INSERT INTO messages VALUES (1, 1, 'hi'), (2, 1, 'yo');
    """)
    setup.close()

    crashed = subprocess.run([sys.executable, "-c", CHILD, path, mode])

    check = sqlite3.connect(path)
    messages = check.execute("SELECT count(*) FROM messages").fetchone()[0]
    chats = check.execute("SELECT count(*) FROM chats").fetchone()[0]
    print(f"{mode:11}  exit code {crashed.returncode}  messages left: {messages}  chats left: {chats}")
    check.close()
```

```text
autocommit   exit code 1  messages left: 0  chats left: 1
transaction  exit code 1  messages left: 2  chats left: 1
```

- **autocommit:** the first DELETE committed the moment it finished. The crash left a chat with no messages: half the operation.
- **transaction:** `BEGIN` made both DELETEs one unit. The crash came before `COMMIT`, so when the parent opened the file again, the first DELETE had been undone. Nothing happened, which is a state you can safely retry from.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A Go service runs `db.Exec(\"DELETE FROM chat_members WHERE chat_id = ?\", id)` and then `db.Exec(\"DELETE FROM chats WHERE id = ?\", id)` against MySQL with default settings. The pod is killed between the two calls. What's in the database afterwards?",
  "options": ["Both deletes are done", "Neither: MySQL rolls both back", "The members are deleted, the chat still exists", "The chat is deleted, the members still exist"], "answer": 2,
  "explanation": "With autocommit on (MySQL's default), each Exec is its own transaction and committed when it finishes. The second statement never ran." }
```

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "Same two DELETEs, now inside `tx, _ := db.Begin()` ... `tx.Commit()`. The pod is killed after the first `tx.Exec` and before `tx.Commit()`. What's in the database afterwards?",
  "options": ["Both deletes are done", "Neither: the uncommitted transaction is rolled back", "The members are deleted, the chat still exists", "It depends on whether Go's garbage collector ran"], "answer": 1,
  "explanation": "The transaction never reached COMMIT, so none of it survives: the database discards an uncommitted transaction when its connection dies. Section 5 shows how SQLite does it." }
```

## 3. BEGIN, COMMIT, ROLLBACK

An explicit transaction is three statements: `BEGIN` starts it, `COMMIT` makes all its changes permanent and visible to other connections at once, `ROLLBACK` throws them all away. (`END` is another name for COMMIT.)

```python
import sqlite3

conn = sqlite3.connect(":memory:", autocommit=True)
conn.executescript("""
CREATE TABLE accounts (id INTEGER PRIMARY KEY, owner TEXT, balance INTEGER NOT NULL CHECK (balance >= 0));
INSERT INTO accounts VALUES (1, 'kim', 100), (2, 'lee', 20);
""")
conn.execute("BEGIN")
conn.execute("UPDATE accounts SET balance = balance - 30 WHERE id = 1")
conn.execute("UPDATE accounts SET balance = balance + 30 WHERE id = 2")
print(conn.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall(), conn.in_transaction)
conn.execute("ROLLBACK")
print(conn.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall(), conn.in_transaction)
```

```text
[(1, 70), (2, 50)] True
[(1, 100), (2, 20)] False
```

Inside the transaction, **this connection** sees its own changes. `conn.in_transaction` tells you whether a transaction is open. After ROLLBACK, both balances are back, as if nothing happened.

Transactions don't nest: `BEGIN` while one is open fails with `OperationalError: cannot start a transaction within a transaction`.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:', autocommit=True)\nc.execute('CREATE TABLE t(x INTEGER)')\nc.execute('INSERT INTO t VALUES (1)')\nc.execute('BEGIN')\nc.execute('INSERT INTO t VALUES (2)')\nc.execute('INSERT INTO t VALUES (3)')\nc.execute('ROLLBACK')\nc.execute('INSERT INTO t VALUES (4)')\nprint(c.execute('SELECT x FROM t ORDER BY x').fetchall())",
  "answer": "[(1,), (4,)]",
  "explanation": "1 was committed on its own (autocommit). 2 and 3 were in the transaction that was rolled back. 4 is its own transaction again." }
```

## 4. An error doesn't roll back the transaction for you

This one surprises almost everyone. When a statement inside a transaction fails, SQLite undoes **that statement only**; the earlier statements stay, and **the transaction stays open**:

```python
conn.execute("BEGIN")
conn.execute("UPDATE accounts SET balance = balance + 500 WHERE id = 2")
try:
    conn.execute("UPDATE accounts SET balance = balance - 500 WHERE id = 1")
except sqlite3.IntegrityError as e:
    print("IntegrityError:", e)
print(conn.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall(), conn.in_transaction)
conn.execute("ROLLBACK")
print(conn.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall(), conn.in_transaction)
```

```text
IntegrityError: CHECK constraint failed: balance >= 0
[(1, 100), (2, 520)] True
[(1, 100), (2, 20)] False
```

lee got 500 that kim never paid. If the code caught the error and then ran `COMMIT` (or let a later commit pick it up), that half-transfer would become permanent. **Your program decides the outcome:** on any error in a multi-step write, roll back. The next lesson shows the Python construct that does this for you.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:', autocommit=True)\nc.execute('CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT UNIQUE)')\nc.execute('BEGIN')\nc.execute(\"INSERT INTO users(name) VALUES ('ana')\")\ntry:\n    c.execute(\"INSERT INTO users(name) VALUES ('ana')\")\nexcept sqlite3.IntegrityError:\n    pass\nc.execute(\"INSERT INTO users(name) VALUES ('ben')\")\nc.execute('COMMIT')\nprint(c.execute('SELECT name FROM users ORDER BY id').fetchall())",
  "answer": "[('ana',), ('ben',)]",
  "explanation": "Only the failing INSERT was undone. The transaction stayed open, the error was swallowed, and COMMIT made the other two permanent. Whether that's right depends on what the operation meant; usually swallowing it is a bug." }
```

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "When a UNIQUE constraint fails on the third statement of a transaction, SQLite rolls back the first two statements automatically.", "answer": false,
  "explanation": "By default (ABORT) only the failing statement is backed out; earlier changes stay pending and the transaction remains open until you COMMIT or ROLLBACK." }
```

## 5. How a crash gets undone: the rollback journal

How can SQLite undo a DELETE when the process that ran it is dead? In its default mode it works like this:

1. **Before** changing a page of the database file, SQLite copies the page's original content into a separate **rollback journal** file next to the database.
2. Then it changes the database file.
3. At COMMIT, once the changes are safely on disk, it deletes the journal. **That deletion is the instant the transaction commits.**

If the process dies before step 3, the journal is still there (a "hot journal"). The next process that opens the database notices it, copies the original pages back, and the database is exactly as it was before the transaction started. That's what happened in the crash demo, and why SQLite's docs can promise that transactions appear atomic even across an operating system crash or a power failure. MySQL's InnoDB makes the same all-or-nothing promise with a different mechanism; for your code, the rule is the same.

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "In SQLite's default journal mode, at what moment does a transaction become committed?",
  "options": ["When the first statement finishes", "When the rollback journal file is deleted after the changes are on disk", "When the connection is closed", "When the next transaction begins"], "answer": 1,
  "explanation": "Until the journal is deleted, a crash leaves a hot journal and the next open rolls the changes back. After it's deleted, the changes are the database." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "Answer the assessment question again: a crash happens between two DELETEs. What's left in the database, and what decides it?",
  "model": "Never 'both': the second DELETE never ran. With autocommit (each statement its own transaction, the default in SQLite and MySQL), the first DELETE is committed and the second isn't, so the data is half-changed. If both run inside one transaction (BEGIN ... COMMIT) and the crash comes before COMMIT, the database rolls the first DELETE back and neither is done. Whether the statements share a transaction decides it, so multi-step writes belong in one transaction.",
  "explanation": "Atomicity comes from transactions, not from the order of statements." }
```

## 6. What's next

You've seen transactions in raw SQL. Python's `sqlite3` module adds its own layer on top: by default it opens transactions for you before some statements and expects you to call `commit()`. The next lesson shows exactly when, what `with conn:` does, and the new `autocommit` attribute from Python 3.12, and then you'll make a multi-step write atomic yourself.
