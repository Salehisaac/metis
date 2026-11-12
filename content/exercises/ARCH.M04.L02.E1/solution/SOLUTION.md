# Reference solution

```python
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
```

**Why it works**

- **Validation first.** Bad ranges fail before any lock is taken, so a flood of invalid requests can't block valid ones.
- **`BEGIN IMMEDIATE` before the first read.** In SQLite's default (deferred) mode, the transaction only becomes a write transaction at the `INSERT`, so two requests can both run the conflict check, both see a free room, and both insert (the lesson's demo shows exactly that). `IMMEDIATE` "causes the database connection to start a new write immediately", so the second request waits (or fails with "database is locked") until the first has committed, and then its check sees the first booking.
- **`with conn:` after the explicit `BEGIN`.** It commits when the block returns and rolls back when anything raises. The rollback matters: an exception that left the transaction open would keep the write lock and block every other booking.
- **Idempotency before conflicts.** A retried request that already succeeded is the most common "duplicate". If the conflict check ran first, the retry would collide with its own booking and the client would see a 409 for a booking it actually has. Comparing room, member, start and end catches a client bug that reuses a key for a different request.
- **One overlap predicate.** `start_ts < end AND start < end_ts` is the half-open rule. It covers partial, containing and contained overlaps, and lets back-to-back bookings touch.
- **`cancel` is idempotent** because setting a status is naturally idempotent (ARCH.M03.L03). In SQLite `rowcount` counts matched rows, so cancelling twice still reports 1 and only a missing id raises.

**In PostgreSQL** the invariant could live in the schema instead: an exclusion constraint on `(room_id WITH =, tsrange(start, end) WITH &&)` using `btree_gist`, as in the PostgreSQL range-types docs. The database then rejects overlaps even from code paths that forget the check. Not runnable here (no PostgreSQL); with SQLite the serialized transaction is the enforcement.

**Limits:** SQLite serializes *all* writers, not just those for one room. At the design's 1 write per second that's irrelevant; at 1,000 per second you'd want PostgreSQL with the exclusion constraint or per-room row locks.
