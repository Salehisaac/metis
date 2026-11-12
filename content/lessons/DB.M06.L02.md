---
{
  "id": "DB.M06.L02",
  "title": "SQLite locking: one writer, busy timeouts and BEGIN IMMEDIATE",
  "difficulty": "intermediate",
  "minutes": 80,
  "prerequisites": ["DB.M06.L01"],
  "objectives": [
    "Describe SQLite's database-level lock states (SHARED, RESERVED, PENDING, EXCLUSIVE) and which can coexist",
    "Explain Python sqlite3's implicit BEGIN and turn it off with isolation_level=None",
    "Use the busy timeout and explain what 'database is locked' means",
    "Reproduce the deferred-transaction upgrade failure and avoid it with BEGIN IMMEDIATE"
  ],
  "why": "'database is locked' is the most common SQLite error in real apps, and it's always a locking question. Once you can predict which connection holds which lock, the error stops being random. The same reasoning (take the lock you need up front, fail early, retry safely) carries over to row locks in PostgreSQL and MySQL.",
  "applications": [
    "Running a FastAPI app with several worker processes on one SQLite file",
    "Background jobs that write while the web app reads",
    "Choosing BEGIN IMMEDIATE for read-then-write logic"
  ],
  "exercises": ["DB.M06.L02.E1"],
  "sources": [
    {
      "title": "File Locking And Concurrency In SQLite Version 3",
      "url": "https://www.sqlite.org/lockingv3.html",
      "version": "SQLite docs, page updated 2025-05-31; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["The lock states UNLOCKED, SHARED, RESERVED, PENDING and EXCLUSIVE and their definitions", "Many SHARED locks can coexist with at most one RESERVED lock; EXCLUSIVE coexists with nothing", "BEGIN takes no lock; the first SELECT takes SHARED, the first write takes RESERVED, EXCLUSIVE comes at commit", "This describes rollback-journal mode; WAL is described separately"]
    },
    {
      "title": "Transaction (BEGIN, COMMIT, ROLLBACK)",
      "url": "https://www.sqlite.org/lang_transaction.html",
      "version": "SQLite docs, page updated 2026-02-18; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["DEFERRED is the default and starts no transaction until the database is first accessed", "IMMEDIATE starts a write transaction at once and may fail with SQLITE_BUSY", "Upgrading a read transaction to a write fails with SQLITE_BUSY if another connection is already modifying the database"]
    },
    {
      "title": "Register A Callback To Handle SQLITE_BUSY Errors",
      "url": "https://www.sqlite.org/c3ref/busy_handler.html",
      "version": "SQLite C API docs; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["If invoking the busy handler could deadlock (a reader upgrading while a writer waits for EXCLUSIVE), SQLite returns SQLITE_BUSY to the reader at once"]
    },
    {
      "title": "Set A Busy Timeout",
      "url": "https://www.sqlite.org/c3ref/busy_timeout.html",
      "version": "SQLite C API docs; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["The busy timeout sleeps and retries until at least ms milliseconds have passed, then returns SQLITE_BUSY", "A value <= 0 turns off busy handlers"]
    },
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (installed 3.12.3, SQLite 3.45.1)",
      "verified": "2026-11-12",
      "claims": ["connect(timeout=) is how long to wait for a lock before OperationalError; default 5 seconds", "isolation_level defaults to '' (DEFERRED); None disables implicit transactions; it applies while autocommit is LEGACY_TRANSACTION_CONTROL, the 3.12 default"]
    },
    {
      "title": "Write-Ahead Logging",
      "url": "https://www.sqlite.org/wal.html",
      "version": "SQLite docs, page updated 2026-08-25; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["In WAL mode readers don't block writers and a writer doesn't block readers", "There can only be one writer at a time", "journal_mode=WAL is persistent", "WAL doesn't work over a network filesystem"]
    }
  ]
}
---
## 1. One lock for the whole file

L01's model: SQLite locks the **entire database file**, not rows or tables. In the default rollback-journal mode a connection moves through these states:

| State | Meaning | Coexists with |
|---|---|---|
| UNLOCKED | not touching the database | everything |
| **SHARED** | reading | other SHARED, one RESERVED |
| **RESERVED** | "I'm going to write"; changes are still in this connection's memory | SHARED (existing and new ones) |
| PENDING | "I want to commit"; waiting for readers to finish | existing SHARED only, no new ones |
| **EXCLUSIVE** | writing to the file at commit | nothing |

Two rules decide almost every situation:

1. **Only one RESERVED lock at a time.** That's "one writer at a time".
2. **COMMIT needs EXCLUSIVE**, so it waits until every SHARED lock is gone.

And when does a transaction take them? The docs: a `BEGIN` takes **no lock**. The first SELECT takes SHARED, the first INSERT/UPDATE/DELETE takes RESERVED, and EXCLUSIVE comes at COMMIT.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Connection A holds RESERVED (it has updated a row, not yet committed). Which is true?",
  "options": ["Other connections can still read, but none can start writing", "Nobody else can read or write", "Others can write to different tables", "Others can write, and A's commit merges their changes"], "answer": 0,
  "explanation": "RESERVED coexists with SHARED locks (readers), but only one RESERVED lock can exist, so no second writer. The lock is on the whole file, so 'a different table' doesn't help." }
```

## 2. Python's hidden BEGIN

By default (`autocommit` is `LEGACY_TRANSACTION_CONTROL` in Python 3.12 and `isolation_level` is `""`), Python's `sqlite3` **silently sends a `BEGIN`** (DEFERRED) before your first INSERT/UPDATE/DELETE, and the transaction stays open until you call `commit()`. That's convenient for simple scripts and confusing for locking: you can't see when transactions start, and you can't choose `BEGIN IMMEDIATE`.

For this module, open connections with `isolation_level=None`: no hidden BEGIN. Each statement outside a transaction autocommits, and a transaction exists only when you write `BEGIN`.

```python
conn = sqlite3.connect("chat.db", timeout=0.5, isolation_level=None)
```

## 3. The busy timeout: waiting instead of failing

When you need a lock someone else holds, SQLite's **busy handler** sleeps and retries until the timeout has passed, then gives up with `SQLITE_BUSY`, which Python raises as `sqlite3.OperationalError: database is locked`. Python's `timeout=` (in seconds, **default 5.0**) sets it; `PRAGMA busy_timeout` reports it in milliseconds. A timeout of 0 means "fail at once".

Two connections to one file; `a` holds a write transaction:

```python
a = sqlite3.connect(DB, timeout=0.5, isolation_level=None)
b = sqlite3.connect(DB, timeout=0.5, isolation_level=None)

a.execute("BEGIN IMMEDIATE")
a.execute("UPDATE chats SET title = 'General' WHERE id = 1")
attempt("b reads       ", b, "SELECT title FROM chats")
attempt("b begins write", b, "BEGIN IMMEDIATE")
a.execute("COMMIT")
attempt("b begins write", b, "BEGIN IMMEDIATE")
```

(`attempt` runs the SQL, then prints the result or the error and how long it took.)

```console
b reads       : ok [('general',)]
b begins write: OperationalError: database is locked (after 0.5s)
b begins write: ok []
```

`b` can read (and sees the committed `'general'`, not a's uncommitted change). Its attempt to become a second writer waits the full 0.5 s, then fails. Once `a` commits, it succeeds. In a web app, a timeout of a few seconds turns short lock waits into slightly slower requests instead of errors.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:', timeout=2.5)\nprint(conn.execute('PRAGMA busy_timeout').fetchone()[0])",
  "answer": "2500",
  "explanation": "Python's timeout is in seconds; SQLite stores the busy timeout in milliseconds." }
```

## 4. The upgrade trap: when waiting can't help

Now the subtle case, with a 2-second timeout and plain (DEFERRED) `BEGIN`. Both connections read first, then both try to write:

```console
a BEGIN          : ok (0.0s)
a SELECT         : ok (0.0s)
b BEGIN          : ok (0.0s)
b SELECT         : ok (0.0s)
a UPDATE         : ok (0.0s)
b UPDATE         : OperationalError: database is locked (0.0s)
a COMMIT         : OperationalError: database is locked (2.0s)
b ROLLBACK       : ok (0.0s)
a COMMIT (again) : ok (0.0s)
```

Follow the locks:

1. Both SELECTs take SHARED. Fine: many readers.
2. `a UPDATE` takes the one RESERVED lock.
3. `b UPDATE` needs RESERVED too, and fails **instantly despite the 2 s timeout**. Waiting couldn't help: `a` can only commit once `b` drops its SHARED lock, and `b` is waiting for `a`. That's a deadlock, so SQLite's docs say it skips the busy handler and returns SQLITE_BUSY to the reader straight away, "hoping that this will induce the first process to release its read lock".
4. `a COMMIT` needs EXCLUSIVE but `b` still holds SHARED, so `a` waits its full 2 s and fails too.
5. Only when `b` rolls back can `a` commit.

The lesson: **a DEFERRED transaction that reads and then writes can fail at the write, after it has already done work, and waiting won't save it.** Your code must roll back and retry the whole transaction.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "A plain `BEGIN` in SQLite takes the write lock, so no other connection can start writing until you COMMIT.", "answer": false,
  "explanation": "BEGIN (DEFERRED) takes no lock at all. Locks are taken by the first read (SHARED) and the first write (RESERVED)." }
```

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "A job does `BEGIN; SELECT ...; (some Python); UPDATE ...; COMMIT` with a 5 s timeout. Under load it sometimes fails with 'database is locked' on the UPDATE **instantly**, not after 5 s. Why?",
  "options": ["Another connection already holds RESERVED while this one holds SHARED; waiting would deadlock, so SQLite returns BUSY immediately", "The timeout only applies to SELECT", "The busy handler is broken", "SQLite has row locks and the row is taken"], "answer": 0,
  "explanation": "That's the upgrade trap. The fix is to start such transactions with BEGIN IMMEDIATE, so they wait at BEGIN, before reading, where waiting is safe." }
```

## 5. BEGIN IMMEDIATE: take the write lock first

`BEGIN IMMEDIATE` takes RESERVED **at BEGIN**. If another writer is active, it waits there (busy timeout) and may fail with SQLITE_BUSY, but **before your transaction has read or done anything**. Once it succeeds, nobody else can start writing until you finish, so the value you read can't change under you before your write.

- Use **`BEGIN IMMEDIATE`** for any transaction that may write, especially read-then-write.
- Plain `BEGIN` (or no transaction) is fine for read-only work.
- Keep write transactions short: no network calls or slow Python while you hold the lock, because every other writer is waiting.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "import os, sqlite3, tempfile\npath = os.path.join(tempfile.mkdtemp(), 'q.db')\na = sqlite3.connect(path, isolation_level=None)\nb = sqlite3.connect(path, isolation_level=None, timeout=0)\na.execute('CREATE TABLE t (x INTEGER)')\na.execute('BEGIN IMMEDIATE')\nprint(b.execute('SELECT count(*) FROM t').fetchone()[0])\ntry:\n    b.execute('BEGIN IMMEDIATE')\n    print('b got the write lock')\nexcept sqlite3.OperationalError as e:\n    print(e)",
  "answer": "0\ndatabase is locked",
  "explanation": "a holds RESERVED from its BEGIN IMMEDIATE, even before writing. b can still read (0 rows), but can't become a second writer, and with timeout=0 it fails at once." }
```

**WAL mode** (`PRAGMA journal_mode=WAL`, which is persistent) changes the reader side: readers don't block the writer and the writer doesn't block readers, so COMMIT no longer waits for SHARED locks. There is **still only one writer at a time**, so BEGIN IMMEDIATE and the busy timeout still matter. WAL needs all processes on the same host (not a network filesystem).

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Your FastAPI app runs 4 worker processes on one SQLite file, and users report occasional 'database is locked' errors when two people edit chats at once. List two changes and why each helps.",
  "model": "1) Make sure every connection has a busy timeout of a few seconds (the default 5 s in Python, but not 0), so short lock waits become waits, not errors. 2) Start write transactions with BEGIN IMMEDIATE (isolation_level=None and explicit BEGIN IMMEDIATE), so read-then-write transactions wait at BEGIN instead of failing instantly at the upgrade. Also keep write transactions short, and consider WAL mode so readers don't block commits. If writes truly conflict often, SQLite's single writer may be the wrong tool (PostgreSQL has row-level locks).",
  "explanation": "Busy timeout handles waiting; BEGIN IMMEDIATE removes the upgrade deadlock; short transactions reduce waiting." }
```

## 6. Your turn

Package this lesson into two building blocks: `connect()` (busy timeout, no hidden BEGIN) and `write_transaction()`, a context manager like the ones you wrote in PY.M07 that takes the write lock at its first line and always commits or rolls back. The tests open a second connection to check that the lock is really held, and that readers still get through.

```exercise
DB.M06.L02.E1
```
