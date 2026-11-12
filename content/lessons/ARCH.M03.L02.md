---
{
  "id": "ARCH.M03.L02",
  "title": "The transactional outbox",
  "difficulty": "advanced",
  "minutes": 110,
  "prerequisites": ["ARCH.M03.L01"],
  "objectives": [
    "Explain the dual-write problem: why 'commit, then publish' and 'publish, then commit' can each lose or invent events",
    "Write a state change and its outbox event in one transaction",
    "Build a polling relay that publishes in order, records progress per event, retries failures and parks poison events",
    "Explain why an outbox gives at-least-once delivery, never exactly-once, and what that demands of consumers"
  ],
  "why": "Your messenger publishes to Kafka after database writes, and your Go review found a multi-step cross-service flow with no recovery path. The outbox is the standard answer to 'my database and my broker disagree after a crash'. It's small enough to build in an afternoon, and you'll build it here with SQLite.",
  "applications": [
    "Publishing domain events (order placed, invoice paid) to Kafka or RabbitMQ reliably",
    "Emails, webhooks and cache invalidations that must not be lost",
    "Driving sagas: each step's local transaction also records the next message"
  ],
  "exercises": ["ARCH.M03.L02.E1"],
  "sources": [
    {
      "title": "microservices.io: Pattern: Transactional outbox",
      "url": "https://microservices.io/patterns/data/transactional-outbox.html",
      "version": "microservices.io (Chris Richardson), undated page",
      "verified": "2026-11-12",
      "claims": ["Problem: atomically update the database and send messages to a broker; 2PC is not an option", "Solution: store the message in the database first; a separate process sends it to the broker", "Messages are sent if and only if the database transaction commits, in the order the application sent them", "The message relay might publish a message more than once, so consumers must be idempotent", "Relay implementations: polling publisher and transaction log tailing"]
    },
    {
      "title": "Apache Kafka documentation: Message Delivery Semantics",
      "url": "https://kafka.apache.org/44/design/design/",
      "version": "Apache Kafka 4.4 docs",
      "verified": "2026-11-12",
      "claims": ["At least once: messages are never lost but may be redelivered", "Kafka guarantees at-least-once delivery by default"]
    },
    {
      "title": "PostgreSQL docs: SELECT, the locking clause",
      "url": "https://www.postgresql.org/docs/current/sql-select.html",
      "version": "PostgreSQL 18 (current) docs; PostgreSQL is not installed here",
      "verified": "2026-11-12",
      "claims": ["With SKIP LOCKED, selected rows that cannot be locked immediately are skipped", "Skipping locked rows can avoid lock contention with multiple consumers of a queue-like table"]
    },
    {
      "title": "sqlite3: How to use the connection context manager",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["with conn: commits on success and rolls back if the body raises"]
    }
  ]
}
---
## 1. The dual-write problem

An invoice is paid. Two things must happen: the database row says `paid`, and an `invoice.paid` event reaches the broker so the receipt service sends a receipt. The obvious code:

```python
def mark_paid_dual_write(invoice_id):
    with conn:
        conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))
    publish("invoice.paid", {"invoice_id": invoice_id})   # after the commit
```

When the broker is unreachable (here `publish` raises `ConnectionError`):

```console
$ python dualwrite.py
publish failed: broker unreachable
paid | events: []
```

The invoice is paid and no receipt will ever be sent. Swap the order and you get the opposite failure: publish first, then the commit fails, and customers get receipts for payments that were rolled back. There's no order of two separate writes that survives a crash between them. microservices.io frames the problem as "How to atomically update the database and send messages to a message broker?", and lists among its forces: "2PC is not an option."

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A service publishes to Kafka *inside* the database transaction, before the commit, 'so both happen together'. What can still go wrong?",
  "options": ["Nothing, the transaction covers the publish", "The publish succeeds and then the commit fails, so consumers act on a change that was rolled back", "Kafka rejects messages sent from inside a transaction", "The commit becomes slower but stays correct"], "answer": 1,
  "explanation": "The database transaction can't roll back a message that already left. Being 'inside the with block' only orders the calls; it doesn't make the broker part of the transaction." }
```

## 2. The outbox: one transaction, then a relay

The pattern's solution: "the service that sends the message to first store the message in the database", and "a separate process then sends the messages to the message broker." The event becomes a row in an **outbox** table, written in the **same transaction** as the state change:

```python
conn.executescript("""
    CREATE TABLE invoices (id INTEGER PRIMARY KEY, status TEXT NOT NULL);
    CREATE TABLE outbox_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        body TEXT NOT NULL,
        published_at TEXT              -- NULL until the relay has published it
    );
""")


def mark_paid(invoice_id):
    """The state change and the event are ONE transaction: both or neither."""
    with conn:
        conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))
        conn.execute(
            "INSERT INTO outbox_events (topic, body) VALUES (?, ?)",
            ("invoice.paid", json.dumps({"invoice_id": invoice_id})),
        )
```

Now there's only one write that matters, and the database makes it atomic. If the process dies before the commit, neither the payment nor the event exists. If it dies after, both exist, and the event waits in the table until someone publishes it.

That someone is the **relay**, a loop in a worker process:

```python
def publish_pending(send):
    """A minimal relay: oldest first, mark each one right after it was sent."""
    rows = conn.execute(
        "SELECT id, topic, body FROM outbox_events WHERE published_at IS NULL ORDER BY id"
    ).fetchall()
    for event_id, topic, body in rows:
        send(topic, json.loads(body))
        with conn:
            conn.execute("UPDATE outbox_events SET published_at = datetime('now') WHERE id = ?", (event_id,))
    return len(rows)
```

```console
$ python outbox_demo.py        # mark_paid(1), mark_paid(2), then the relay twice
published: 2
broker: [('invoice.paid', {'invoice_id': 1}), ('invoice.paid', {'invoice_id': 2})]
published again: 0
```

In production `send` would be a Kafka or RabbitMQ producer call, and the relay would run every second or so. **No broker is installed here**, so the demos and the exercise use a Python function as the broker.

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "With an outbox, if the broker is down for an hour, the invoices can still be marked paid and no events are lost.", "answer": true,
  "explanation": "The request path only touches the database. Events pile up in the outbox while the broker is down, and the relay publishes them, in order, once it's back. The cost is delay, not loss." }
```

## 3. Why it's at-least-once

Look at the relay loop again: `send(...)`, *then* the `UPDATE ... published_at`. If the relay crashes between those two lines, the event was published but the table still says it wasn't, so the restarted relay publishes it again. Swapping the lines doesn't help: mark first, crash, and the event is never published. That's the dual-write problem again, between the broker and the outbox.

So an outbox gives **at-least-once** delivery. microservices.io says it directly: "The Message relay might publish a message more than once." The broker adds its own duplicates. Kafka's docs define at-least-once as "messages are never lost but may be redelivered" and say "Kafka guarantees at-least-once delivery by default". Either way, **the consumer must be idempotent** (L03).

```quiz
{ "id": "q3", "type": "output",
  "prompt": "The relay crashes right after publishing event 2, before marking it. It restarts and runs again. What does this print?",
  "code": "outbox = {1: \"sent\", 2: \"pending\", 3: \"pending\"}  # state after the crash\nbroker = [\"e1\", \"e2\"]                               # what was published before the crash\n\nfor event_id in sorted(outbox):\n    if outbox[event_id] == \"pending\":\n        broker.append(f\"e{event_id}\")\n        outbox[event_id] = \"sent\"\n\nprint(broker)",
  "answer": "['e1', 'e2', 'e2', 'e3']",
  "explanation": "Event 2 left before the crash but was still marked pending, so the restarted relay sends it again. Nothing is lost; one event is duplicated. That's at-least-once." }
```

## 4. A relay you can run in production

The minimal relay above has gaps. Here's what a real one handles, and what you'll implement in the exercise:

| Concern | Rule |
|---|---|
| **Progress** | Commit after **each** published event, so a crash repeats at most one event. |
| **Order** | Read oldest first. If an event fails, **stop the batch**: publishing event 3 while event 2 is pending lets consumers see them out of order. The pattern's benefits include messages being sent "in the order they were sent by the application". |
| **Retries** | Count `attempts`, keep `last_error`, retry on the next run. |
| **Poison events** | After N failures, mark the event `dead` so it stops blocking the rest, and alert someone. |
| **Batch size** | Publish at most N per run, so one huge backlog doesn't hold a transaction or memory for minutes. |
| **Several relays** | Two relays reading the same pending rows publish duplicates. Run one, or claim rows with `SELECT ... FOR UPDATE SKIP LOCKED` on PostgreSQL. Its docs say this "can be used to avoid lock contention with multiple consumers accessing a queue-like table". Not runnable here: SQLite has no row locks. |

microservices.io names two ways to build the relay: a **polling publisher** (this lesson) and **transaction log tailing**, which reads the database's change log instead of querying a table. Tools exist for log tailing, but they need database-specific setup that this machine doesn't have.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "Event 7 fails to publish (the broker rejects its payload). Events 8 and 9 are pending. What should the relay do on this run?",
  "options": ["Skip 7 and publish 8 and 9", "Record the failure on 7, stop this batch, and retry from 7 next run; park 7 as dead after N attempts", "Delete event 7", "Retry 7 in a tight loop until it succeeds"], "answer": 1,
  "explanation": "Stopping keeps the order, counting attempts makes the failure visible, and parking a poison event after N tries keeps it from blocking everything forever. A tight loop hammers a broker that's already failing." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Design review",
  "prompt": "Your Go system deletes a user across services in sequence: profile service RPC, then messages service RPC, then the local users row, with no compensation. Using what you've learned, sketch a more robust design and name what it still can't guarantee.",
  "model": "Do the local part in one transaction: mark the user as 'deleting' (or delete the row) and insert outbox events like user.deleted in the same transaction. A relay publishes them; the profile and messages services consume user.deleted and delete their data in their own local transactions, idempotently, because delivery is at-least-once. Failures are retried by the relay or consumer instead of leaving a half-deleted user, and dead events are visible. What it can't guarantee: that all services are consistent at the same instant. It's eventually consistent, so for a while the profile may still exist after the user row is gone. If a step can genuinely fail for business reasons, you need compensating actions (a saga), not just retries.",
  "explanation": "Outbox plus idempotent consumers turns 'lost halfway' into 'finished later'." }
```

## 5. Your turn: orders with an outbox

You'll write `place_order` (order and event in one transaction) and `relay_once` (in-order publishing with per-event commits, retries, a batch limit and dead-lettering). One test kills the relay mid-batch and checks, from a second connection, that the event it already published is recorded as sent.

```exercise
ARCH.M03.L02.E1
```
