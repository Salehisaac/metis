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
    raise NotImplementedError


def cancel(conn: sqlite3.Connection, booking_id: int) -> None:
    """Set the booking's status to 'cancelled'. Cancelling twice is fine. KeyError if there is no such booking."""
    raise NotImplementedError
