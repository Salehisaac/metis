---
{
  "id": "DB.M03.L03",
  "title": "Testing the rollback",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["DB.M03.L02"],
  "objectives": [
    "Turn 'all or nothing' into concrete assertions: committed for others on success; nothing on any connection, no open transaction and the error propagated on failure",
    "Explain why checking only a second connection misses a missing rollback",
    "Make a multi-step write fail at a chosen step, with data that breaks a constraint or with monkeypatch",
    "Use pytest's tmp_path for a file database that two connections can share",
    "Judge a test suite by asking which realistic bug each test would catch"
  ],
  "why": "DB.M03's second outcome is 'wrap multi-step writes and test the rollback'. A transaction you haven't tested is a transaction you're assuming works, and the bugs here (an early commit, a swallowed error, a missing rollback) all pass the happy-path test. You've never written tests before PY.M04; this lesson is the first time you write tests whose job is to catch someone else's bug.",
  "applications": [
    "Proving that transfers, sign-ups and chat creation can't half-happen",
    "Reviewing a pull request that 'adds a transaction': which test shows it works?",
    "Testing service code whose last step calls another service that can fail"
  ],
  "exercises": ["DB.M03.L03.E1"],
  "sources": [
    {
      "title": "pytest: How to use temporary directories and files in tests",
      "url": "https://docs.pytest.org/en/stable/how-to/tmp_path.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["The tmp_path fixture provides a temporary directory unique to each test function, as a pathlib.Path"]
    },
    {
      "title": "pytest: How to monkeypatch/mock modules and environments",
      "url": "https://docs.pytest.org/en/stable/how-to/monkeypatch.html",
      "version": "pytest stable docs (9.x); verified locally with pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["monkeypatch.setattr patches a function or attribute for the test", "All modifications are undone after the requesting test function has finished"]
    },
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["in_transaction is True if a transaction is active (uncommitted changes)", "The connection context manager rolls back when the body raises, and the exception is still raised"]
    }
  ]
}
---
## 1. What "all or nothing" means as assertions

Here's a function to test, in a small bank (the same pattern as your exercise, on different tables). It credits first and debits second, so an overdraft fails **after** two writes have already run:

```python
# bank.py
import sqlite3

SCHEMA = """
CREATE TABLE accounts (id INTEGER PRIMARY KEY, owner TEXT NOT NULL, balance INTEGER NOT NULL CHECK (balance >= 0));
CREATE TABLE ledger (id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), delta INTEGER NOT NULL);
INSERT INTO accounts VALUES (1, 'kim', 100), (2, 'lee', 20);
"""


def open_bank(path):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def notify(account_id, amount):
    """Pretend to call another service."""


def transfer(conn, from_id, to_id, amount):
    """Move amount between accounts and record both ledger lines, all or nothing."""
    with conn:
        conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_id))
        conn.execute("INSERT INTO ledger (account_id, delta) VALUES (?, ?)", (to_id, amount))
        conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_id))
        conn.execute("INSERT INTO ledger (account_id, delta) VALUES (?, ?)", (from_id, -amount))
        notify(to_id, amount)
```

"All or nothing" is really four separate promises, and each needs its own check:

| Promise | Who can observe it being broken | Assertion |
|---|---|---|
| On success, everything is **committed** | Only **another connection** | A second connection sees all the changes |
| On failure, **nothing** is written | **Every** connection, including the caller's | Before == after, on both connections |
| No transaction is **left open** | The caller's connection | `conn.in_transaction is False` |
| The **error reaches the caller** | The caller | `pytest.raises(...)` |

The second row is the subtle one. If the function raises *without rolling back*, the other connection sees nothing (the changes were never committed), so a test that only checks the other connection **passes**. But the changes are still pending on the caller's connection, and the next `commit()` anywhere, maybe in unrelated code, makes them permanent. Check the caller's connection too.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A function raises after two INSERTs and never calls rollback() (no `with conn:`). The test checks only a second connection and finds no new rows. What does that prove?",
  "options": ["The function is atomic", "Nothing: the rows were never committed, so the second connection can't see them either way. They're still pending on the first connection", "The rows were rolled back by SQLite automatically", "The INSERTs never ran"], "answer": 1,
  "explanation": "Uncommitted changes are invisible to other connections whether or not they'll be rolled back. Check the caller's connection and in_transaction too." }
```

## 2. Two connections need a file: `tmp_path`

An in-memory database exists only inside one connection, so "another connection" needs a file. pytest's built-in **`tmp_path`** fixture gives every test function its own fresh temporary directory (a `pathlib.Path`). Ask for it by naming it as a parameter, the same way you'd ask for `capsys`:

```python
# test_bank.py
import sqlite3

import pytest

import bank


def balances(conn):
    return conn.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall()


def test_transfer_is_committed(tmp_path):
    conn = bank.open_bank(tmp_path / "bank.db")
    bank.transfer(conn, 1, 2, 30)
    other = sqlite3.connect(tmp_path / "bank.db")
    assert balances(other) == [(1, 70), (2, 50)]
    assert other.execute("SELECT count(*) FROM ledger").fetchone() == (2,)


def test_overdraft_changes_nothing(tmp_path):
    conn = bank.open_bank(tmp_path / "bank.db")
    other = sqlite3.connect(tmp_path / "bank.db")
    with pytest.raises(sqlite3.IntegrityError):
        bank.transfer(conn, 2, 1, 500)  # lee only has 20
    for c in (conn, other):
        assert balances(c) == [(1, 100), (2, 20)]
        assert c.execute("SELECT count(*) FROM ledger").fetchone() == (0,)
    assert conn.in_transaction is False
```

- The success test checks from `other`: that's the only way to see "committed".
- The failure test makes step 3 fail with **real data** that breaks a constraint (the CHECK on balance), after steps 1 and 2 ran. Then it checks **both** connections and the open-transaction flag.
- Each test builds its own database, so tests can't affect each other, and the order they run in doesn't matter.

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "Two tests that both use tmp_path / 'bank.db' share the same database file, so the second test sees the first test's transfers.", "answer": false,
  "explanation": "tmp_path is a different directory for every test function, so each test gets its own bank.db." }
```

## 3. Failing at a chosen step: monkeypatch

Sometimes no data can make a step fail, like the `notify` call at the end of `transfer`. Then replace that step with one that raises. pytest's **`monkeypatch`** fixture does it safely: `monkeypatch.setattr(module, "name", replacement)` swaps the attribute for this test only and restores it afterwards.

```python
def test_failure_after_the_last_write_rolls_back(tmp_path, monkeypatch):
    def broken_notify(account_id, amount):
        raise ConnectionError("notification service down")

    monkeypatch.setattr(bank, "notify", broken_notify)
    conn = bank.open_bank(tmp_path / "bank.db")
    with pytest.raises(ConnectionError):
        bank.transfer(conn, 1, 2, 30)
    assert balances(conn) == [(1, 100), (2, 20)]
```

```text
$ pytest -q test_bank.py
...                                                                      [100%]
3 passed in 0.13s
```

This works because `transfer` looks up the name `notify` in the `bank` module **each time it runs**, and that's the name the test replaced. The rule: **patch the name where the code under test looks it up.** (If bank.py did `from notifications import notify`, you'd still patch `bank.notify`, not `notifications.notify`.)

**Is rolling back here right?** The money moved, only the notification failed. Rolling back is the safe default; if the business wants the transfer kept anyway, the notification belongs *after* the transaction (or in a queue, which you suggested in the assessment). Tests make that decision visible instead of accidental.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\n\ndef notify(x):\n    raise ConnectionError('down')\n\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE t(x INTEGER)')\ntry:\n    with c:\n        c.execute('INSERT INTO t VALUES (1)')\n        notify(1)\nexcept ConnectionError as e:\n    print('error:', e)\nprint(c.execute('SELECT count(*) FROM t').fetchone()[0], c.in_transaction)",
  "answer": "error: down\n0 False",
  "explanation": "Any exception leaving the with block rolls back the transaction, not just database errors. The insert is gone and no transaction is open." }
```

## 4. Would this test catch the bug? Check by breaking the code

A test suite is only as good as the bugs it catches. The fastest way to find out: break the code on purpose and see whether a test fails. Remove the transaction from `transfer` (replace `with conn:` by `if True:`) and rerun:

```text
$ pytest -q --tb=no test_bank.py
=========================== short test summary info ============================
FAILED test_bank.py::test_transfer_is_committed - assert [(1, 100), (2, 20)] ...
FAILED test_bank.py::test_overdraft_changes_nothing - assert [(1, 600), (2, 2...
FAILED test_bank.py::test_failure_after_the_last_write_rolls_back - assert [(...
3 failed in 0.12s
```

All three fail, each for its own reason: nothing was committed (other sees 100 and 20); the overdraft left account 1 credited with 500, pending on `conn`; the notify failure left the transfer pending. Then put `with conn:` back. This is called **mutation testing** when a tool does it for you; doing it by hand for the one line that matters most is enough here.

The exercise automates exactly this: `test_meta.py` swaps in five broken versions of a function and checks that your tests notice each one.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "A colleague's only test for create_order calls it once with valid data and checks the order row exists on the same connection. Which bug can this test NOT catch?",
  "options": ["A typo in the INSERT's table name", "A missing commit (nothing is ever saved for other connections)", "A wrong column value in the inserted row", "A function that raises on valid data"], "answer": 1,
  "explanation": "The same connection sees its own uncommitted rows, so the test passes without a commit. Only a second connection (or in_transaction) shows it." }
```

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3, tempfile, os\nwith tempfile.TemporaryDirectory() as d:\n    p = os.path.join(d, 'a.db')\n    c = sqlite3.connect(p)\n    c.execute('CREATE TABLE t(x INTEGER UNIQUE)')\n    c.execute('INSERT INTO t VALUES (1)')\n    try:\n        c.execute('INSERT INTO t VALUES (1)')\n    except sqlite3.IntegrityError:\n        pass\n    other = sqlite3.connect(p)\n    print(other.execute('SELECT count(*) FROM t').fetchone()[0], c.execute('SELECT count(*) FROM t').fetchone()[0], c.in_transaction)\n    c.close(); other.close()",
  "answer": "0 1 True",
  "explanation": "The duplicate was undone on its own, but nothing rolled back the transaction: the first insert is still pending. The other connection sees 0, the same connection sees 1, and a transaction is open." }
```

## 5. What you don't need to test

You don't need to test that SQLite survives a power cut; its rollback journal (DB.M03.L01) does that for any transaction. What you test is that **your code puts all the steps in one transaction** and handles failure correctly. If the tests above pass, a crash in the middle of `transfer` is also safe, because there's only one commit point.

## 6. Your turn

This time the function is correct and **you write the tests**. `membership.leave_chat` posts a "left the chat" message and removes a membership as one transaction. `test_meta.py` runs your tests against five buggy versions. Write your tests from the docstring in `membership.py` first, run pytest, and only then read the bug descriptions in the failures.

```exercise
DB.M03.L03.E1
```
