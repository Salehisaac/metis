---
{
  "id": "DB.M03.L02",
  "title": "Transactions in sqlite3: commit, rollback, with conn: and autocommit",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["DB.M03.L01"],
  "objectives": [
    "Predict when Python's sqlite3 opens a transaction in its default mode, and what other connections see before and after commit()",
    "State exactly what `with conn:` does and doesn't do (commit, rollback, re-raise; no close, no BEGIN of its own)",
    "Compare the three values of the 3.12 autocommit attribute and predict what `with conn:` does in each",
    "Avoid two traps: executescript() committing a pending transaction, and PRAGMA foreign_keys having no effect inside a transaction",
    "Turn a multi-step write that commits after each step into one atomic transaction"
  ],
  "why": "The previous lesson used raw BEGIN and COMMIT. Real Python code goes through the sqlite3 module, which by default opens transactions for you before some statements and not others. If you don't know its rules, you either lose writes (no commit) or keep half of them (commit in the wrong place). `with conn:` is the tool you'll use for every multi-step write in this academy, so its exact semantics matter.",
  "applications": [
    "Creating a chat with its members and first message in one unit",
    "Any 'write several rows or none' operation in a repository or service layer",
    "Reading other people's sqlite3 code and spotting a missing commit or a half-committed operation"
  ],
  "exercises": ["DB.M03.L02.E1"],
  "sources": [
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "autocommit defaults to LEGACY_TRANSACTION_CONTROL; the default will change to False in a future release",
        "In legacy mode with isolation_level not None, a transaction is opened implicitly before INSERT, UPDATE, DELETE or REPLACE; other statements get no implicit transaction handling",
        "close() does not commit; in legacy or True mode no implicit transaction control is executed, so commit() before closing",
        "Connection as context manager: commits if the body finishes without exceptions; rolls back if the commit fails or the body raises; the exception is still raised",
        "The context manager neither implicitly opens a new transaction nor closes the connection; it does nothing if no transaction is open or if autocommit is True",
        "autocommit=False is the recommended value: a transaction is always open, commit() and rollback() open a new one, and close() rolls back pending changes",
        "autocommit=True: SQLite's autocommit mode; commit() and rollback() have no effect",
        "executescript() in legacy mode commits a pending transaction first",
        "setconfig(SQLITE_DBCONFIG_ENABLE_FKEY) was added in 3.12"
      ]
    },
    {
      "title": "SQLite Foreign Key Support",
      "url": "https://www.sqlite.org/foreignkeys.html",
      "version": "SQLite docs (current)",
      "verified": "2026-11-12",
      "claims": ["Enabling or disabling foreign keys inside a multi-statement transaction has no effect and returns no error"]
    }
  ]
}
---
## 1. Python adds a layer: the default mode

In DB.M03.L01 you connected with `autocommit=True` and wrote BEGIN and COMMIT yourself. A plain `sqlite3.connect(path)` behaves differently. Its `autocommit` attribute is `sqlite3.LEGACY_TRANSACTION_CONTROL` (the pre-3.12 behaviour, still the default in 3.12), and in that mode:

- Before an **INSERT, UPDATE, DELETE or REPLACE**, if no transaction is open, sqlite3 sends `BEGIN` for you.
- **SELECT and DDL** (CREATE TABLE...) don't open one.
- Nothing commits until **you** call `conn.commit()`.

```python
import os
import sqlite3

if os.path.exists("shop.db"):
    os.remove("shop.db")
conn = sqlite3.connect("shop.db")
print(conn.autocommit == sqlite3.LEGACY_TRANSACTION_CONTROL, repr(conn.isolation_level))
conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT NOT NULL)")
print("after CREATE:", conn.in_transaction)
conn.execute("SELECT count(*) FROM orders").fetchone()
print("after SELECT:", conn.in_transaction)
conn.execute("INSERT INTO orders (item) VALUES ('book')")
print("after INSERT:", conn.in_transaction)

other = sqlite3.connect("shop.db")
print("other sees:", other.execute("SELECT count(*) FROM orders").fetchone()[0])
conn.commit()
print("after commit:", conn.in_transaction, "| other sees:", other.execute("SELECT count(*) FROM orders").fetchone()[0])

conn.execute("INSERT INTO orders (item) VALUES ('pen')")
conn.close()  # no commit!
print("after close without commit, other sees:", other.execute("SELECT count(*) FROM orders").fetchone()[0])
```

```text
True ''
after CREATE: False
after SELECT: False
after INSERT: True
other sees: 0
after commit: False | other sees: 1
after close without commit, other sees: 1
```

- The INSERT opened a transaction; **another connection can't see** the row until `commit()`.
- `close()` **doesn't commit**. The 'pen' order is gone. A forgotten `commit()` is the most common sqlite3 bug: everything looks fine inside the program, and the data never reaches the file.
- In the in-memory examples of DB.M01 and DB.M02 you never noticed, because one connection always sees its own uncommitted changes.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "a and b are two connections to the same file. What does this print?",
  "code": "import sqlite3, tempfile, os\nwith tempfile.TemporaryDirectory() as d:\n    path = os.path.join(d, 'q.db')\n    a = sqlite3.connect(path)\n    a.execute('CREATE TABLE t(x)')\n    a.execute('INSERT INTO t VALUES (1)')\n    b = sqlite3.connect(path)\n    print(b.execute('SELECT count(*) FROM t').fetchone()[0], end=' ')\n    a.commit()\n    print(b.execute('SELECT count(*) FROM t').fetchone()[0])\n    a.close(); b.close()",
  "answer": "0 1",
  "explanation": "CREATE TABLE runs without a transaction, so b sees the table. The INSERT opened a transaction on a; b sees the row only after a.commit()." }
```

## 2. `with conn:`: commit or roll back, exactly once

A `with` block runs setup code before its body and guaranteed exit code after it, even when an exception leaves the body. You'll see how that works in PY.M07.L02 (it's Python's answer to Go's `defer`). For a sqlite3 connection, the exit code is:

- body finished **without an exception** → `commit()`
- body **raised** → `rollback()`, and the exception **continues** to your caller
- if the commit itself fails → rollback

```python
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT NOT NULL)")

with conn:
    conn.execute("INSERT INTO orders (item) VALUES ('book')")
    conn.execute("INSERT INTO orders (item) VALUES ('pen')")
print(conn.execute("SELECT count(*) FROM orders").fetchone()[0], conn.in_transaction)

try:
    with conn:
        conn.execute("INSERT INTO orders (item) VALUES ('lamp')")
        conn.execute("INSERT INTO orders (item) VALUES (NULL)")
except sqlite3.IntegrityError as e:
    print("IntegrityError:", e)
print(conn.execute("SELECT count(*) FROM orders").fetchone()[0], conn.in_transaction)

class OutOfStock(Exception):
    pass

try:
    with conn:
        conn.execute("INSERT INTO orders (item) VALUES ('desk')")
        raise OutOfStock("desk")
except OutOfStock:
    print("OutOfStock raised, rolled back")
print(conn.execute("SELECT count(*) FROM orders").fetchone()[0])
print(conn.execute("SELECT 1").fetchone())  # still open
```

```text
2 False
IntegrityError: NOT NULL constraint failed: orders.item
2 False
OutOfStock raised, rolled back
2
(1,)
```

- 'lamp' was rolled back together with the failing NULL insert: all or nothing.
- **Any** exception rolls back, including your own (`OutOfStock`), not only database errors.
- **What it does not do:** it doesn't close the connection (the last line still works), and it doesn't send BEGIN itself. In the default mode the first INSERT inside the block opens the transaction, as in section 1.

In Go terms, `with conn:` is `tx, err := db.Begin()`, `defer tx.Rollback()`, ..., `return tx.Commit()`, already written for you.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT UNIQUE)')\nwith c:\n    c.execute(\"INSERT INTO users(name) VALUES ('ana')\")\ntry:\n    with c:\n        c.execute(\"INSERT INTO users(name) VALUES ('ben')\")\n        c.execute(\"INSERT INTO users(name) VALUES ('ana')\")\nexcept sqlite3.IntegrityError:\n    print('duplicate')\nprint(c.execute('SELECT name FROM users ORDER BY id').fetchall())",
  "answer": "duplicate\n[('ana',)]",
  "explanation": "The first block committed 'ana'. In the second, the duplicate raised, so the block rolled back 'ben' too, and re-raised the error for the except to print." }
```

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "After `with conn:` finishes, the connection is closed, like a file after `with open(...)`.", "answer": false,
  "explanation": "The connection's context manager only commits or rolls back. Close it yourself (or use contextlib.closing)." }
```

## 3. Trap: `executescript()` commits first

In the default mode, `executescript()` **commits any pending transaction** before running its script, and the script's statements run in autocommit mode. Inside a `with conn:` block that silently breaks atomicity:

```python
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT NOT NULL)")
try:
    with conn:
        conn.execute("INSERT INTO orders (item) VALUES ('book')")
        conn.executescript("INSERT INTO orders (item) VALUES ('pen');")
        raise RuntimeError("something failed later")
except RuntimeError:
    pass
print(conn.execute("SELECT item FROM orders ORDER BY id").fetchall())
```

```text
[('book',), ('pen',)]
```

The block rolled back, but there was nothing left to roll back. Use `executescript()` for setup scripts only, never inside a unit of work.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE t(x INTEGER)')\nc.execute('INSERT INTO t VALUES (1)')\nc.executescript('INSERT INTO t VALUES (2);')\nc.execute('INSERT INTO t VALUES (3)')\nc.rollback()\nprint(c.execute('SELECT x FROM t ORDER BY x').fetchall())",
  "answer": "[(1,), (2,)]",
  "explanation": "executescript committed the pending insert of 1, then ran its own insert of 2 in autocommit mode. Only 3 was in the transaction that rollback() discarded." }
```

## 4. The `autocommit` attribute (Python 3.12)

Python 3.12 added `autocommit`, set with `sqlite3.connect(path, autocommit=...)`. The docs **recommend `False`**, and say the default will change to `False` in a future Python release.

| `autocommit` | When is a transaction open? | `commit()` / `rollback()` | `with conn:` | `close()` with pending changes |
|---|---|---|---|---|
| `LEGACY_TRANSACTION_CONTROL` (default in 3.12) | Opened implicitly before INSERT/UPDATE/DELETE/REPLACE | Work | Commits or rolls back | Changes lost (not committed) |
| `False` (recommended) | **Always**: opened at connect, and again right after every commit/rollback | Work, then open a new transaction | Commits or rolls back | Rolled back |
| `True` | Only when you run `BEGIN` yourself | **No effect** | **Does nothing** | Whatever you didn't COMMIT is lost |

Here's the same failing block in each mode:

```python
def setup(**kwargs):
    conn = sqlite3.connect(":memory:", **kwargs)
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT NOT NULL)")
    conn.commit()
    return conn

for kwargs in [{}, {"autocommit": True}, {"autocommit": False}]:
    conn = setup(**kwargs)
    try:
        with conn:
            conn.execute("INSERT INTO orders (item) VALUES ('lamp')")
            conn.execute("INSERT INTO orders (item) VALUES (NULL)")
    except sqlite3.IntegrityError:
        pass
    print(kwargs or "default", "-> rows:", conn.execute("SELECT count(*) FROM orders").fetchone()[0],
          "in_transaction:", conn.in_transaction)
```

```text
default -> rows: 0 in_transaction: False
{'autocommit': True} -> rows: 1 in_transaction: False
{'autocommit': False} -> rows: 0 in_transaction: True
```

- With `autocommit=True`, 'lamp' **survived**: each statement committed on its own, and `with conn:` had no transaction to roll back. In that mode, multi-step writes need explicit `conn.execute("BEGIN")` ... `conn.execute("COMMIT")`, as in the previous lesson.
- With `autocommit=False`, `in_transaction` is `True` even after the rollback: that's the "always a transaction open" rule, not a leak.

**The foreign key trap with `autocommit=False`.** `PRAGMA foreign_keys = ON` has no effect inside a transaction, and with `autocommit=False` a transaction is open from the moment you connect:

```python
conn = sqlite3.connect(":memory:", autocommit=True)
conn.execute("PRAGMA foreign_keys = ON")
conn.autocommit = False
print(conn.execute("PRAGMA foreign_keys").fetchone(), conn.in_transaction)

late = sqlite3.connect(":memory:", autocommit=False)
late.execute("PRAGMA foreign_keys = ON")
print(late.execute("PRAGMA foreign_keys").fetchone(), late.in_transaction)
```

```text
(1,) True
(0,) True
```

No error, just no foreign keys. Either set the PRAGMA in autocommit mode and then switch to `False` (as above), or use `conn.setconfig(sqlite3.SQLITE_DBCONFIG_ENABLE_FKEY, True)`, new in 3.12, which works in any mode.

**Which mode in this academy?** The exercises use the default mode, because that's what most existing code (and most tutorials) use. For new code of your own, `autocommit=False` is what the docs recommend. In both, the rule is the same: **every multi-step write goes inside one `with conn:` block, and nothing in it calls `commit()`.**

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:', autocommit=True)\nc.execute('CREATE TABLE t(x INTEGER NOT NULL)')\ntry:\n    with c:\n        c.execute('INSERT INTO t VALUES (1)')\n        c.execute('INSERT INTO t VALUES (NULL)')\nexcept sqlite3.IntegrityError:\n    pass\nprint(c.execute('SELECT count(*) FROM t').fetchone()[0])",
  "answer": "1",
  "explanation": "With autocommit=True each statement commits on its own, and `with conn:` does nothing. The first insert stays." }
```

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "`conn = sqlite3.connect(path, autocommit=False)` followed by `conn.execute(\"PRAGMA foreign_keys = ON\")`. What happens when you then insert a message for a chat that doesn't exist?",
  "options": ["IntegrityError: FOREIGN KEY constraint failed", "The insert succeeds: the PRAGMA ran inside the already-open transaction and had no effect", "The PRAGMA raises OperationalError", "The connection switches to autocommit mode"], "answer": 1,
  "explanation": "With autocommit=False a transaction is open from connect(). Changing foreign_keys inside a transaction is silently ignored. Set it before switching to autocommit=False, or use setconfig." }
```

## 5. Your turn

`create_group_chat` writes a chat, its memberships and a first message, and calls `commit()` after every step. When a member id is unknown, the caller gets an error, but a half-created group is already committed. That's your assessment's crash question again, in code: a failure in the middle of several writes.

The tests open the database file with two connections: the one your function uses, and another that only sees committed data. Read the test file before you start; the assertion messages say what each check is looking for.

```exercise
DB.M03.L02.E1
```
