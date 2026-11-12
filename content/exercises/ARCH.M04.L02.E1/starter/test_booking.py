import importlib
import sqlite3
import sys

import pytest

H = 3600
NINE = 1_767_258_000  # 2026-01-01 09:00 UTC, a multiple of 15 minutes


def load():
    sys.modules.pop("booking", None)
    return importlib.import_module("booking")


class SpyConn(sqlite3.Connection):
    statements: list

    def execute(self, sql, *args):
        self.statements.append(" ".join(sql.split()).upper())
        return super().execute(sql, *args)


def db():
    b = load()
    conn = sqlite3.connect(":memory:", factory=SpyConn)
    conn.statements = []
    conn.executescript(b.SCHEMA)
    conn.execute("INSERT INTO rooms VALUES (1, 'Atlas'), (2, 'Borealis')")
    conn.commit()
    conn.statements.clear()
    return b, conn


def test_book_returns_the_booking():
    b, conn = db()
    got = b.book(conn, 1, "ana", NINE, NINE + H, "k1")
    assert got == {"id": got["id"], "room_id": 1, "member": "ana", "start": NINE, "end": NINE + H, "status": "confirmed"}
    assert not conn.in_transaction, "book must commit"


def test_overlap_is_rejected():
    b, conn = db()
    b.book(conn, 1, "ana", NINE, NINE + H, "k1")
    for start, end in [(NINE + 30 * 60, NINE + 2 * H), (NINE - H, NINE + 15 * 60), (NINE + 15 * 60, NINE + 30 * 60), (NINE - H, NINE + 2 * H)]:
        with pytest.raises(b.BookingConflict):
            b.book(conn, 1, "bo", start, end, f"k-{start}-{end}")


def test_touching_bookings_are_allowed():
    b, conn = db()
    b.book(conn, 1, "ana", NINE, NINE + H, "k1")
    b.book(conn, 1, "bo", NINE + H, NINE + 2 * H, "k2")    # starts when ana's ends
    b.book(conn, 1, "cy", NINE - H, NINE, "k3")            # ends when ana's starts


def test_other_rooms_and_cancelled_bookings_dont_block():
    b, conn = db()
    first = b.book(conn, 1, "ana", NINE, NINE + H, "k1")
    b.book(conn, 2, "bo", NINE, NINE + H, "k2")
    b.cancel(conn, first["id"])
    b.cancel(conn, first["id"])                            # twice is fine
    b.book(conn, 1, "cy", NINE, NINE + H, "k3")


def test_validation():
    b, conn = db()
    bad = [(NINE, NINE), (NINE + H, NINE), (NINE, NINE + 4 * H + 15 * 60), (NINE + 60, NINE + H), (NINE, NINE + H + 1)]
    for start, end in bad:
        with pytest.raises(ValueError):
            b.book(conn, 1, "ana", start, end, f"k-{start}-{end}")
    b.book(conn, 1, "ana", NINE, NINE + 4 * H, "k-max")    # exactly 4 hours is allowed


def test_unknown_room():
    b, conn = db()
    with pytest.raises(b.RoomNotFound):
        b.book(conn, 99, "ana", NINE, NINE + H, "k1")


def test_retry_with_same_key_returns_same_booking():
    b, conn = db()
    first = b.book(conn, 1, "ana", NINE, NINE + H, "k1")
    again = b.book(conn, 1, "ana", NINE, NINE + H, "k1")   # would conflict with itself if not deduplicated
    assert again == first
    assert conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 1


def test_same_key_different_request_is_rejected():
    b, conn = db()
    b.book(conn, 1, "ana", NINE, NINE + H, "k1")
    with pytest.raises(b.IdempotencyMismatch):
        b.book(conn, 1, "ana", NINE + 2 * H, NINE + 3 * H, "k1")


def test_check_and_insert_run_in_an_immediate_transaction():
    b, conn = db()
    b.book(conn, 1, "ana", NINE, NINE + H, "k1")
    first_sql = next(s for s in conn.statements)
    assert first_sql.startswith("BEGIN IMMEDIATE"), "take the write lock before checking for conflicts"


def test_failed_booking_leaves_no_open_transaction():
    b, conn = db()
    b.book(conn, 1, "ana", NINE, NINE + H, "k1")
    with pytest.raises(b.BookingConflict):
        b.book(conn, 1, "bo", NINE, NINE + H, "k2")
    assert not conn.in_transaction, "roll back on failure, or the write lock stays held"
    b.book(conn, 1, "bo", NINE + H, NINE + 2 * H, "k3")


def test_cancel_unknown_booking():
    b, conn = db()
    with pytest.raises(KeyError):
        b.cancel(conn, 42)
