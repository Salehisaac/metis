# Reference solution

```python
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
```

**Why it works**

- **One transaction for the order and its event.** Both inserts sit in the same `with conn:` block, so they commit together or not at all. The crash test proves it: when the outbox insert fails, the order insert is rolled back too. This is microservices.io's guarantee, "messages are guaranteed to be sent if and only if the database transaction commits", minus the "sent" part, which the relay delivers.
- **`lastrowid` inside the transaction.** The payload needs the order id, which only exists after the first insert. Reading it inside the block keeps everything in one unit of work.
- **Commit after every publish.** If the relay dies after publishing event 1, the database already says event 1 is `sent`, so a restarted relay continues with event 2. The worst case is the tiny window between `publish` returning and the commit: that event gets published again. That's **at-least-once** delivery, which is why consumers must be idempotent (next lesson).
- **Stop the batch on failure.** Publishing event 3 while event 2 is still pending would let consumers see them out of order (for example "order.shipped" before "order.placed"). Breaking out keeps the order, and the next run retries from the oldest pending event.
- **Park poison events.** An event the broker always rejects would block everything behind it forever. After `max_attempts` it becomes `dead`: out of the way, still in the table with its `last_error`, ready for a human to inspect and requeue.
- **`except Exception`, not `BaseException`.** A broker error is a normal failure to record. A crash (`KeyboardInterrupt`, `SystemExit`, or the test's `Crash`) must stop the relay, not be written to `last_error`.

**Limits of this version**

- **One relay at a time.** Two relay processes would both read the same pending rows and publish duplicates. With PostgreSQL you'd claim rows with `SELECT ... FOR UPDATE SKIP LOCKED`, or run a single relay (not runnable here: SQLite has no row locks).
- **Retry timing.** It retries on every run. Real relays wait longer between attempts (exponential backoff, next lesson) by storing a `next_attempt_at` column.
- **Transaction log tailing** (reading the database's change log, as tools like Debezium do) is the other relay style microservices.io lists. It avoids polling but needs database-specific infrastructure.
