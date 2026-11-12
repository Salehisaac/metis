# Reference solution

```python
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
```

**Why it works**

- **`free_slots` is a pure function.** No I/O, so its edge cases (touching, partial overlaps, unsorted and overlapping bookings, a window that isn't a whole number of slots) are tested with plain lists. The overlap test is the same half-open predicate as in L02, so a booking that ends at 9:15 doesn't block the 9:15 slot.
- **Two separate `try` blocks.** A read failure and a write failure are different events: if the read fails, there's no point attempting the write (Redis is probably down), and if only the write fails, the answer is still good. Both are logged, and both mark the answer as degraded.
- **Only `redis.RedisError` is caught.** The loader's exceptions escape, because without the database there is no correct answer. Caching is the optional part.
- **The source string is for operators.** Returning `'db-degraded'` lets the endpoint add a header or a metric, so a dashboard shows "availability served without cache" during a Redis outage, which is exactly the "detection" column of the failure-mode table.
- **`[]` is a real value.** `json.dumps([])` is `"[]"`, a stored string, so `cached is not None` treats a fully booked day as a hit.

**What this doesn't cover:** a Redis that *hangs* instead of refusing connections. Then every request waits for the client's timeout before degrading. In production, set short socket timeouts on the Redis client (redis-py has `socket_timeout` and `socket_connect_timeout`) so "slow Redis" becomes "Redis error" quickly. fakeredis can't simulate a hang, so this exercise only tests the refusal case.

**Alternative:** a circuit breaker that stops calling Redis for a few seconds after several failures saves the per-request error cost during an outage. Add it when the failure logs show the degraded path is hot; it's one more state machine to test.
