"""A payment consumer that tolerates duplicate deliveries, and a retry helper with exponential backoff."""
import sqlite3

SCHEMA = """
CREATE TABLE invoices (id INTEGER PRIMARY KEY, paid_cents INTEGER NOT NULL DEFAULT 0);
CREATE TABLE payments (invoice_id INTEGER NOT NULL, amount_cents INTEGER NOT NULL, message_id TEXT NOT NULL);
CREATE TABLE processed_messages (
    consumer TEXT NOT NULL,
    message_id TEXT NOT NULL,
    PRIMARY KEY (consumer, message_id)
);
"""


class UnknownInvoice(Exception):
    pass


class TransientError(Exception):
    """A failure worth retrying (timeout, connection reset, 503)."""


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
