```python
def connect(path, busy_timeout=5.0):
    return sqlite3.connect(path, timeout=busy_timeout, isolation_level=None)


@contextmanager
def write_transaction(conn):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
```

**Why it works**

- `timeout=` is the busy timeout: when another connection holds a lock you need, SQLite sleeps and retries for up to
  that many seconds before raising `OperationalError: database is locked`. Python takes seconds; `PRAGMA busy_timeout`
  reports milliseconds, hence 5000 and 250 in the tests.
- `isolation_level=None` stops Python's legacy behaviour of silently sending `BEGIN` (DEFERRED) before your first
  INSERT/UPDATE/DELETE. Now a transaction exists only when you start one, so you can choose `BEGIN IMMEDIATE`.
- `BEGIN IMMEDIATE` takes the RESERVED (write) lock **at BEGIN**. A plain `BEGIN` takes no lock at all, so
  `test_write_lock_is_taken_at_the_start` would fail: `b` could still start its own write transaction.
- Readers keep working while you hold RESERVED: only one writer at a time, but many readers, until your COMMIT
  briefly needs EXCLUSIVE.
- `except BaseException` also rolls back on `KeyboardInterrupt` and similar, then `raise` re-raises the original
  exception unchanged. `COMMIT` sits after the `try`, so it only runs when the body finished normally. Either way the
  lock is released, which the last test checks.

**Alternative:** Python 3.12's `sqlite3.connect(path, autocommit=False)` gives PEP 249 behaviour (always inside a
transaction, `commit()` starts the next one). It still opens transactions with a deferred BEGIN, so for
"take the write lock first" you'd still issue `BEGIN IMMEDIATE` yourself with `isolation_level=None` as above.
