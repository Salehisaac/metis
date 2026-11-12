"""Connections and write transactions for a multi-process SQLite app."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager


def connect(path: str, busy_timeout: float = 5.0) -> sqlite3.Connection:
    """Open `path` for explicit transaction control.

    - No implicit BEGIN: statements outside a transaction autocommit.
    - Wait up to `busy_timeout` seconds for a lock before raising OperationalError.
    """
    return sqlite3.connect(path, timeout=busy_timeout, isolation_level=None)


@contextmanager
def write_transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run the body as one write transaction that holds the write lock from the start.

    with write_transaction(conn):
        conn.execute(...)

    Commits if the body finishes; rolls back and re-raises if it raises.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
