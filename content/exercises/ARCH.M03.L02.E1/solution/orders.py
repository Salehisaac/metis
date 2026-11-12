"""Orders with a transactional outbox. Use conn.execute for every statement (the tests watch it)."""
import json
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
    if not customer.strip():
        raise ValueError("customer required")
    if total_cents <= 0:
        raise ValueError("total must be positive")
    with conn:
        cur = conn.execute("INSERT INTO orders (customer, total_cents) VALUES (?, ?)", (customer, total_cents))
        order_id = cur.lastrowid
        event = {"order_id": order_id, "customer": customer, "total_cents": total_cents}
        conn.execute("INSERT INTO outbox (topic, payload) VALUES (?, ?)", ("order.placed", json.dumps(event)))
    return order_id


def relay_once(conn: sqlite3.Connection, publish, batch_size: int = 10, max_attempts: int = 5) -> int:
    """Publish up to batch_size pending events, oldest first. Return how many were published.

    publish(topic: str, payload: dict) sends one event to the broker and raises on failure.
    - After each successful publish, mark that event 'sent' and commit straight away.
    - On a failure: add 1 to attempts, store str(error) in last_error, set status 'dead' once
      attempts reaches max_attempts, commit, and stop this batch (later events must not overtake it).
    """
    pending = conn.execute(
        "SELECT id, topic, payload, attempts FROM outbox WHERE status = 'pending' ORDER BY id LIMIT ?",
        (batch_size,),
    ).fetchall()
    published = 0
    for event_id, topic, payload, attempts in pending:
        try:
            publish(topic, json.loads(payload))
        except Exception as e:  # noqa: BLE001  (any broker failure is recorded, not raised)
            attempts += 1
            status = "dead" if attempts >= max_attempts else "pending"
            with conn:
                conn.execute(
                    "UPDATE outbox SET attempts = ?, last_error = ?, status = ? WHERE id = ?",
                    (attempts, str(e), status, event_id),
                )
            break
        with conn:
            conn.execute("UPDATE outbox SET status = 'sent' WHERE id = ?", (event_id,))
        published += 1
    return published
