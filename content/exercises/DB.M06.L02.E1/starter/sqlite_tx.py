"""Connections and write transactions for a multi-process SQLite app."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager


def connect(path: str, busy_timeout: float = 5.0) -> sqlite3.Connection:
    """Open `path` for explicit transaction control.

    - No implicit BEGIN: statements outside a transaction autocommit.
    - Wait up to `busy_timeout` seconds for a lock before raising OperationalError.
    """
    raise NotImplementedError


@contextmanager
def write_transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run the body as one write transaction that holds the write lock from the start.

    with write_transaction(conn):
        conn.execute(...)

    Commits if the body finishes; rolls back and re-raises if it raises.
    """
    raise NotImplementedError
    yield conn
