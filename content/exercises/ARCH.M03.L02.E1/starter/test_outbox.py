import importlib
import json
import sqlite3
import sys

import pytest


def load():
    sys.modules.pop("orders", None)
    return importlib.import_module("orders")


def db(path=":memory:", factory=sqlite3.Connection):
    o = load()
    conn = sqlite3.connect(path, factory=factory)
    conn.executescript(o.SCHEMA)
    return o, conn


def outbox(conn):
    return conn.execute("SELECT id, topic, payload, status, attempts, last_error FROM outbox ORDER BY id").fetchall()


class Broker:
    def __init__(self, fail_on=(), always_fail=()):
        self.sent = []
        self.fail_on = list(fail_on)          # order_ids that fail once each
        self.always_fail = set(always_fail)   # order_ids that always fail

    def __call__(self, topic, payload):
        oid = payload["order_id"]
        if oid in self.always_fail:
            raise ConnectionError(f"broker rejected {oid}")
        if oid in self.fail_on:
            self.fail_on.remove(oid)
            raise ConnectionError("broker unreachable")
        self.sent.append((topic, oid))


class CrashOnOutbox(sqlite3.Connection):
    """Simulates the process dying right before the outbox insert."""

    def execute(self, sql, *args):
        if "outbox" in sql and sql.lstrip().upper().startswith("INSERT"):
            raise RuntimeError("crash before the outbox insert")
        return super().execute(sql, *args)


def test_place_order_writes_order_and_event():
    o, conn = db()
    oid = o.place_order(conn, "ana", 1999)
    assert conn.execute("SELECT customer, total_cents FROM orders WHERE id = ?", (oid,)).fetchone() == ("ana", 1999)
    (_, topic, payload, status, attempts, err), = outbox(conn)
    assert (topic, status, attempts, err) == ("order.placed", "pending", 0, None)
    assert json.loads(payload) == {"order_id": oid, "customer": "ana", "total_cents": 1999}
    assert not conn.in_transaction, "place_order must commit"


def test_place_order_is_atomic():
    o, conn = db(factory=CrashOnOutbox)
    with pytest.raises(RuntimeError):
        o.place_order(conn, "ana", 1999)
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0, "order saved without its event"


def test_place_order_validates_input():
    o, conn = db()
    for customer, total in [("", 100), ("   ", 100), ("ana", 0), ("ana", -5)]:
        with pytest.raises(ValueError):
            o.place_order(conn, customer, total)
    assert outbox(conn) == []
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_relay_publishes_in_order_and_marks_sent():
    o, conn = db()
    ids = [o.place_order(conn, c, 100) for c in ("a", "b", "c")]
    broker = Broker()
    assert o.relay_once(conn, broker) == 3
    assert broker.sent == [("order.placed", i) for i in ids]
    assert [row[3] for row in outbox(conn)] == ["sent", "sent", "sent"]
    assert o.relay_once(conn, broker) == 0, "sent events must not be published again"
    assert len(broker.sent) == 3


def test_relay_respects_batch_size():
    o, conn = db()
    for c in "abcde":
        o.place_order(conn, c, 100)
    broker = Broker()
    assert o.relay_once(conn, broker, batch_size=2) == 2
    assert o.relay_once(conn, broker, batch_size=2) == 2
    assert o.relay_once(conn, broker, batch_size=2) == 1
    assert [oid for _, oid in broker.sent] == [1, 2, 3, 4, 5]


def test_relay_failure_keeps_event_pending_and_stops():
    o, conn = db()
    a, b, _c = (o.place_order(conn, x, 100) for x in "abc")
    broker = Broker(fail_on=[b])
    assert o.relay_once(conn, broker) == 1
    assert broker.sent == [("order.placed", a)]
    rows = outbox(conn)
    assert rows[1][3:] == ("pending", 1, "broker unreachable")
    assert rows[2][3:] == ("pending", 0, None), "a later event must not overtake a failed one"


def test_relay_retries_on_next_run():
    o, conn = db()
    a, b, c = (o.place_order(conn, x, 100) for x in "abc")
    broker = Broker(fail_on=[b])
    o.relay_once(conn, broker)
    assert o.relay_once(conn, broker) == 2
    assert [oid for _, oid in broker.sent] == [a, b, c]


def test_relay_parks_poison_event_as_dead():
    o, conn = db()
    a, b = o.place_order(conn, "a", 100), o.place_order(conn, "b", 100)
    broker = Broker(always_fail=[a])
    for _ in range(3):
        assert o.relay_once(conn, broker, max_attempts=3) == 0
    assert outbox(conn)[0][3:5] == ("dead", 3)
    assert o.relay_once(conn, broker, max_attempts=3) == 1, "once parked, the event no longer blocks the rest"
    assert broker.sent == [("order.placed", b)]


class Crash(BaseException):
    """The relay process dies (not an ordinary exception)."""


def test_each_success_is_committed_before_the_next_publish(tmp_path):
    path = str(tmp_path / "shop.db")
    o, conn = db(path)
    o.place_order(conn, "a", 100)
    b = o.place_order(conn, "b", 100)

    def publish(topic, payload):
        if payload["order_id"] == b:
            raise Crash()

    with pytest.raises(Crash):
        o.relay_once(conn, publish)
    other = sqlite3.connect(path)
    status = dict(other.execute("SELECT id, status FROM outbox").fetchall())
    assert status[1] == "sent", "event 1 was published, so 'sent' must already be committed"
