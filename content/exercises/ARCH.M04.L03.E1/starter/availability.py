"""Room availability for the booking service: computed from bookings, cached, and degrading gracefully."""
import json  # noqa: F401  (you'll need it)
import logging

import redis  # noqa: F401  (redis.RedisError is the base class of its errors)

log = logging.getLogger("availability")
SLOT = 15 * 60
AVAIL_TTL = 30  # N2 in the design: the view may be up to 30 s stale


def free_slots(bookings: list[tuple[int, int]], open_ts: int, close_ts: int, slot: int = SLOT) -> list[int]:
    """Start times of the free slots in [open_ts, close_ts), in order.

    Slots start at open_ts, open_ts + slot, ...; a slot must end by close_ts.
    A slot is free if it overlaps no booking. Bookings are half-open (start, end) pairs, in any order;
    they may overlap each other or extend past the window.
    """
    raise NotImplementedError


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
    raise NotImplementedError
