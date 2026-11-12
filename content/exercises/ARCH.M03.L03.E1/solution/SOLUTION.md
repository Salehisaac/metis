# Reference solution

```python
def handle_payment(conn: sqlite3.Connection, message: dict, consumer: str = "billing") -> bool:
    """Apply a 'payment.captured' message: {"id": str, "invoice_id": int, "amount_cents": int}.

    In ONE transaction: record (consumer, message id) in processed_messages, add amount_cents to the
    invoice's paid_cents, and insert a payments row. Return True if applied, False if this consumer
    already processed this message id (then change nothing).
    Raise UnknownInvoice (and change nothing, so a redelivery can try again) if the invoice doesn't exist.
    """
    with conn:
        try:
            conn.execute(
                "INSERT INTO processed_messages (consumer, message_id) VALUES (?, ?)", (consumer, message["id"])
            )
        except sqlite3.IntegrityError:
            return False  # seen before: the earlier delivery already applied it
        cur = conn.execute(
            "UPDATE invoices SET paid_cents = paid_cents + ? WHERE id = ?",
            (message["amount_cents"], message["invoice_id"]),
        )
        if cur.rowcount == 0:
            raise UnknownInvoice(message["invoice_id"])  # rolls back the marker too
        conn.execute(
            "INSERT INTO payments (invoice_id, amount_cents, message_id) VALUES (?, ?, ?)",
            (message["invoice_id"], message["amount_cents"], message["id"]),
        )
    return True


def backoff_delay(attempt: int, base: float = 0.5, cap: float = 8.0, rng=None) -> float:
    """Seconds to wait before retry number `attempt` (1 = first retry).

    Without rng: min(cap, base * 2 ** (attempt - 1)).
    With rng (has .uniform(a, b)): a random value in [0, that delay], i.e. rng.uniform(0, delay).
    """
    delay = min(cap, base * 2 ** (attempt - 1))
    return delay if rng is None else rng.uniform(0, delay)


def with_retries(fn, sleep, max_attempts: int = 4, rng=None):
    """Call fn() and return its result, retrying only on TransientError.

    At most max_attempts calls in total. Before retry n (n = 1, 2, ...) call sleep(backoff_delay(n, rng=rng)).
    If the last attempt fails, re-raise its TransientError. Any other exception propagates at once.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except TransientError:
            if attempt == max_attempts:
                raise
            sleep(backoff_delay(attempt, rng=rng))
```

**Why it works**

- **The marker and the effect share one transaction.** This is the idempotent-consumer pattern from microservices.io: after starting the transaction, insert the message id into a processed-messages table whose primary key makes "the INSERT ... fail if the message has been already processed". Because the marker commits only together with the payment, there are exactly two possible states: neither happened (a redelivery will apply it) or both happened (a redelivery is skipped).
- **The database detects the duplicate.** A `SELECT` check followed by an insert would have a gap where two deliveries handled concurrently both see "not processed". The primary key closes it, the same way the conditional `UPDATE` did in ARCH.M01.L02.
- **Per-consumer keys.** The audit consumer and the billing consumer both legitimately process `m-1`, so the key is `(consumer, message_id)`, not the message id alone.
- **Failures roll back the marker.** `UnknownInvoice` is raised inside the `with` block, so the marker disappears with everything else. If you marked first and committed separately, the message would be "processed" forever without its effect.
- **Bounded, capped, transient-only retries.** Doubling spreads retries out; the cap stops the waits from growing without limit; `max_attempts` stops a permanent outage from retrying forever; and a `ValueError` (a bad payload will be just as bad next time) fails at once. The AWS article's warning applies: "When failures are caused by overload, retries that increase load can make matters significantly worse."
- **Injected `sleep` and `rng`.** Tests pass `sleeps.append` and `random.Random(seed)`, so they run in microseconds and are deterministic. Production passes `time.sleep` (or `asyncio.sleep` in an async variant) and the `random` module.

**Alternatives**

- **Naturally idempotent writes** need no marker table: `UPDATE orders SET status = 'paid' WHERE id = ?` gives the same result however often it runs. Prefer them when the domain allows. Increments, inserts and emails aren't naturally idempotent.
- **Use the business key** instead of a message id when one exists (for example a unique `payment_id` column on `payments`), so even two *different* messages for the same payment can't double-apply.
- Libraries such as `tenacity` package retry policies. The logic is short enough that writing it once by hand is the better lesson.
