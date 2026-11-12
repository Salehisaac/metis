"""Orders with a transactional outbox. Use conn.execute for every statement (the tests watch it)."""
import json  # noqa: F401  (you'll need it)
import sqlite3

SCHEMA = """
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer TEXT NOT NULL,
    total_cents INTEGER NOT NULL
);
CREATE TABLE outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    payload TEXT NOT NULL,                    -- JSON
    status TEXT NOT NULL DEFAULT 'pending',   -- pending | sent | dead
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT
);
"""


def place_order(conn: sqlite3.Connection, customer: str, total_cents: int) -> int:
    """Insert the order and its 'order.placed' outbox event in ONE transaction; return the order id.

    payload: {"order_id": ..., "customer": ..., "total_cents": ...}
    ValueError (and nothing written) if customer is blank or total_cents <= 0.
    """
    raise NotImplementedError


def relay_once(conn: sqlite3.Connection, publish, batch_size: int = 10, max_attempts: int = 5) -> int:
    """Publish up to batch_size pending events, oldest first. Return how many were published.

    publish(topic: str, payload: dict) sends one event to the broker and raises on failure.
    - After each successful publish, mark that event 'sent' and commit straight away.
    - On a failure: add 1 to attempts, store str(error) in last_error, set status 'dead' once
      attempts reaches max_attempts, commit, and stop this batch (later events must not overtake it).
    """
    raise NotImplementedError
