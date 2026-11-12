import importlib
import random
import sqlite3
import sys

import pytest


def load():
    sys.modules.pop("billing", None)
    return importlib.import_module("billing")


def db():
    b = load()
    conn = sqlite3.connect(":memory:")
    conn.executescript(b.SCHEMA)
    conn.execute("INSERT INTO invoices (id) VALUES (1)")
    conn.commit()
    return b, conn


def paid(conn, invoice_id=1):
    return conn.execute("SELECT paid_cents FROM invoices WHERE id = ?", (invoice_id,)).fetchone()[0]


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


MSG = {"id": "m-1", "invoice_id": 1, "amount_cents": 500}


def test_duplicate_delivery_is_applied_once():
    b, conn = db()
    assert b.handle_payment(conn, MSG) is True
    assert b.handle_payment(conn, dict(MSG)) is False
    assert paid(conn) == 500
    assert count(conn, "payments") == 1


def test_different_messages_all_apply():
    b, conn = db()
    b.handle_payment(conn, MSG)
    assert b.handle_payment(conn, {"id": "m-2", "invoice_id": 1, "amount_cents": 250}) is True
    assert paid(conn) == 750


def test_dedup_is_per_consumer():
    b, conn = db()
    b.handle_payment(conn, MSG, consumer="billing")
    assert b.handle_payment(conn, MSG, consumer="audit") is True
    assert count(conn, "processed_messages") == 2


def test_failure_leaves_no_marker_so_redelivery_works():
    b, conn = db()
    msg = {"id": "m-9", "invoice_id": 2, "amount_cents": 100}
    with pytest.raises(b.UnknownInvoice):
        b.handle_payment(conn, msg)
    assert count(conn, "processed_messages") == 0, "a failed message must not be marked processed"
    assert count(conn, "payments") == 0
    conn.execute("INSERT INTO invoices (id) VALUES (2)")
    conn.commit()
    assert b.handle_payment(conn, msg) is True
    assert paid(conn, 2) == 100


def test_backoff_doubles_and_caps():
    b = load()
    assert [b.backoff_delay(n) for n in range(1, 7)] == [0.5, 1.0, 2.0, 4.0, 8.0, 8.0]
    assert b.backoff_delay(3, base=1.0, cap=3.0) == 3.0


def test_backoff_jitter_is_within_the_delay():
    b = load()
    assert b.backoff_delay(3, rng=random.Random(3)) == random.Random(3).uniform(0, 2.0)
    rng = random.Random(1)
    values = [b.backoff_delay(10, rng=rng) for _ in range(50)]
    assert all(0 <= v <= 8.0 for v in values) and len(set(values)) > 1


class Flaky:
    def __init__(self, failures, error=None):
        self.failures = failures
        self.error = error
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error or sys.modules["billing"].TransientError("503")
        return "ok"


def test_retries_transient_errors_then_succeeds():
    b = load()
    sleeps = []
    fn = Flaky(failures=2)
    assert b.with_retries(fn, sleeps.append) == "ok"
    assert fn.calls == 3
    assert sleeps == [0.5, 1.0]


def test_gives_up_after_max_attempts():
    b = load()
    sleeps = []
    fn = Flaky(failures=99)
    with pytest.raises(b.TransientError):
        b.with_retries(fn, sleeps.append, max_attempts=4)
    assert fn.calls == 4
    assert sleeps == [0.5, 1.0, 2.0], "no sleep after the final failure"


def test_permanent_errors_are_not_retried():
    b = load()
    sleeps = []
    fn = Flaky(failures=1, error=ValueError("bad payload"))
    with pytest.raises(ValueError):
        b.with_retries(fn, sleeps.append)
    assert (fn.calls, sleeps) == (1, [])
