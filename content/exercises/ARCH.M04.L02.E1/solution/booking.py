"""Room booking, implemented from the design doc (ARCH.M04.L02).

Times are Unix seconds. Intervals are half-open: [start, end).
"""
import sqlite3

SCHEMA = """
CREATE TABLE rooms (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE bookings (
    id INTEGER PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES rooms(id),
    member TEXT NOT NULL,
    start_ts INTEGER NOT NULL,
    end_ts INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed',      -- confirmed | cancelled
    idempotency_key TEXT NOT NULL UNIQUE
);
CREATE INDEX bookings_room_start ON bookings (room_id, start_ts);
"""

SLOT = 15 * 60          # bookings start and end on 15-minute boundaries
MAX_LENGTH = 4 * 3600   # at most 4 hours


class RoomNotFound(Exception):
    pass


class BookingConflict(Exception):
    pass


class IdempotencyMismatch(Exception):
    """The key was already used for a different request."""


def book(conn: sqlite3.Connection, room_id: int, member: str, start: int, end: int, key: str) -> dict:
    """Create a confirmed booking and return it as a dict:
    {"id", "room_id", "member", "start", "end", "status"}.

    Rules, in this order:
    1. ValueError unless start < end, end - start <= MAX_LENGTH, and both are multiples of SLOT.
    2. In ONE write transaction started with conn.execute("BEGIN IMMEDIATE"):
       a. if a booking with this idempotency key exists: return it if room_id, member, start and end
          all match, otherwise raise IdempotencyMismatch;
       b. RoomNotFound if the room doesn't exist;
       c. BookingConflict if a *confirmed* booking for the same room overlaps [start, end);
       d. insert and return the new booking.
    """
    if not (start < end and end - start <= MAX_LENGTH and start % SLOT == 0 and end % SLOT == 0):
        raise ValueError("bookings are 15-minute aligned, non-empty and at most 4 hours")
    conn.execute("BEGIN IMMEDIATE")  # take the write lock BEFORE reading, so no one books in between
    with conn:  # commit on return, roll back (and release the lock) on any exception
        existing = conn.execute(
            "SELECT id, room_id, member, start_ts, end_ts, status FROM bookings WHERE idempotency_key = ?", (key,)
        ).fetchone()
        if existing is not None:
            if existing[1:5] != (room_id, member, start, end):
                raise IdempotencyMismatch(key)
            return _as_dict(existing)
        if conn.execute("SELECT 1 FROM rooms WHERE id = ?", (room_id,)).fetchone() is None:
            raise RoomNotFound(room_id)
        clash = conn.execute(
            "SELECT id FROM bookings WHERE room_id = ? AND status = 'confirmed' AND start_ts < ? AND ? < end_ts",
            (room_id, end, start),
        ).fetchone()
        if clash is not None:
            raise BookingConflict(f"room {room_id} is taken by booking {clash[0]}")
        cur = conn.execute(
            "INSERT INTO bookings (room_id, member, start_ts, end_ts, idempotency_key) VALUES (?, ?, ?, ?, ?)",
            (room_id, member, start, end, key),
        )
        return _as_dict((cur.lastrowid, room_id, member, start, end, "confirmed"))


def _as_dict(row) -> dict:
    return dict(zip(("id", "room_id", "member", "start", "end", "status"), row))


def cancel(conn: sqlite3.Connection, booking_id: int) -> None:
    """Set the booking's status to 'cancelled'. Cancelling twice is fine. KeyError if there is no such booking."""
    with conn:
        cur = conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
    if cur.rowcount == 0:
        raise KeyError(booking_id)
