"""Room availability for the booking service: computed from bookings, cached, and degrading gracefully."""
import json
import logging

import redis

log = logging.getLogger("availability")
SLOT = 15 * 60
AVAIL_TTL = 30  # N2 in the design: the view may be up to 30 s stale


def free_slots(bookings: list[tuple[int, int]], open_ts: int, close_ts: int, slot: int = SLOT) -> list[int]:
    """Start times of the free slots in [open_ts, close_ts), in order.

    Slots start at open_ts, open_ts + slot, ...; a slot must end by close_ts.
    A slot is free if it overlaps no booking. Bookings are half-open (start, end) pairs, in any order;
    they may overlap each other or extend past the window.
    """
    free = []
    start = open_ts
    while start + slot <= close_ts:
        end = start + slot
        if not any(b_start < end and start < b_end for b_start, b_end in bookings):
            free.append(start)
        start = end
    return free


def availability_key(room_id: int, open_ts: int) -> str:
    return f"cache:avail:{room_id}:{open_ts}"


def get_availability(r, load_bookings, room_id: int, open_ts: int, close_ts: int) -> tuple[list[int], str]:
    """Return (free slot starts, source) where source is 'cache', 'db' or 'db-degraded'.

    load_bookings(room_id, open_ts, close_ts) -> list of (start, end) pairs: the database query.
    - Cache hit: return the cached list with 'cache'.
    - Miss: compute from load_bookings, store as JSON with ex=AVAIL_TTL, return with 'db'.
    - Any redis.RedisError on the read or the write: log a warning on the 'availability' logger,
      still answer from the database, and return 'db-degraded'.
    - Errors from load_bookings propagate (we can't answer without the database).
    """
    key = availability_key(room_id, open_ts)
    degraded = False
    try:
        cached = r.get(key)
        if cached is not None:
            return json.loads(cached), "cache"
    except redis.RedisError as e:
        log.warning("availability cache read failed for %s, using the database: %s", key, e)
        degraded = True
    slots = free_slots(load_bookings(room_id, open_ts, close_ts), open_ts, close_ts)
    if not degraded:
        try:
            r.set(key, json.dumps(slots), ex=AVAIL_TTL)
        except redis.RedisError as e:
            log.warning("availability cache write failed for %s: %s", key, e)
            degraded = True
    return slots, "db-degraded" if degraded else "db"
