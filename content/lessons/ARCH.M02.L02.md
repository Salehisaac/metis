---
{
  "id": "ARCH.M02.L02",
  "title": "Invalidation after commit and stale reads",
  "difficulty": "intermediate",
  "minutes": 110,
  "prerequisites": ["ARCH.M02.L01"],
  "objectives": [
    "Invalidate by deleting the key, after the database commit, and explain why each half of that rule matters",
    "Trace the interleaving that makes 'delete, then commit' serve stale data, and the rarer race that remains with 'commit, then delete'",
    "Decide what to do when the invalidation itself fails, without swallowing the error",
    "State what bounds staleness in a cache-aside design (TTL) and when to bypass the cache"
  ],
  "why": "Invalidate-after-commit is in the Go code you shipped. This lesson is about knowing why that order is right, what it still doesn't protect against, and what to do when the delete fails, so you can defend the design in a review instead of copying a pattern.",
  "applications": [
    "Any write path for cached data: edits, deletes, status changes",
    "Code review of 'update the cache' vs 'delete the cache' changes",
    "Explaining a 'users still see the old value' bug report"
  ],
  "exercises": ["ARCH.M02.L02.E1"],
  "sources": [
    {
      "title": "Redis docs: Redis cache-aside with redis-py",
      "url": "https://redis.io/docs/latest/develop/use-cases/cache-aside/redis-py",
      "version": "redis.io docs (latest, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["On a write, update the primary and then delete the cache key so the next read repopulates it", "Delete the cache key rather than rewriting it; keeping cache and primary in sync from the application opens the door to subtle ordering bugs", "The TTL is the upper bound on how long a stale value can be served"]
    },
    {
      "title": "Redis docs: Redis cache-aside",
      "url": "https://redis.io/docs/latest/develop/use-cases/cache-aside/",
      "version": "redis.io docs (latest, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Invalidate on write so stale data windows stay within a configured bound", "DEL on write gives explicit invalidation; per-key EX/PX TTL bounds staleness"]
    },
    {
      "title": "sqlite3: How to use the connection context manager",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["with conn: commits when the body finishes without an exception"]
    },
    {
      "title": "fakeredis documentation",
      "url": "https://fakeredis.readthedocs.io/en/latest/",
      "version": "fakeredis docs (latest); installed fakeredis 2.40.0",
      "verified": "2026-11-12",
      "claims": ["Connection errors can be simulated by setting the server's connected attribute to False"]
    }
  ]
}
---
## 1. The write path: delete, don't update

When data changes, the cached copy is wrong. Two options:

- **Update the cache** with the new value.
- **Delete the key** and let the next read reload it (L01's read path).

The redis.io guide is clear: "delete the cache key rather than rewriting it". Keeping the cache and the database in sync from the application "opens the door to subtle ordering bugs". Here's one. Two admins change a price at the same moment:

| Step | Admin A | Admin B | DB | Cache |
|---|---|---|---|---|
| 1 | `UPDATE price = 900`, commit | | 900 | 1000 |
| 2 | | `UPDATE price = 800`, commit | 800 | 1000 |
| 3 | | `SET cache 800` | 800 | 800 |
| 4 | `SET cache 900` (A was slower) | | 800 | **900** |

The database says 800 and the cache says 900 until the TTL runs out. With delete, both writers delete the key, and whatever happens the next read loads 800. **Delete is idempotent and order-free; set isn't.**

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Why is deleting the key safer than writing the new value into it?",
  "options": ["DEL is faster than SET", "Two deletes in any order give the same result, and the next read loads whatever is committed; two SETs can land in the wrong order", "SET doesn't support TTLs", "Redis can't store updated values"], "answer": 1,
  "explanation": "Deletes commute: their order doesn't matter. The cost is one extra miss after each write, which is almost always worth it." }
```

## 2. Why "after commit"

Now the order of the two writes: the database update and the cache delete. Here's a deterministic simulation with two real SQLite connections (a writer and a concurrent reader) and fakeredis. The reader uses L01's read path, and it slips in between the writer's two steps:

```python
def run(order):
    ...                                              # reset: price 1000, cache warm with 1000
    writer.execute("UPDATE products SET price = 900 WHERE id = 1")
    if order == "delete, then commit":
        r.delete(KEY)
        read_through()                               # a reader slips in here
        writer.commit()
    else:
        writer.commit()
        r.delete(KEY)
        read_through()                               # same reader, same moment
```

```console
$ python race.py
delete, then commit  -> db=900 cache=1000 ttl=300
commit, then delete  -> db=900 cache=900 ttl=300
```

With "delete, then commit", the reader misses, reads the database **before the commit** (so it sees the old committed 1000, because uncommitted changes are invisible to other connections) and caches it with a fresh 300-second TTL. The invalidation was wasted, and the stale copy got a full new lifetime.

The same trap exists without an explicit `delete` call before the commit. A FastAPI dependency that commits **after** `yield` (ARCH.M01.L02) runs after your endpoint, and if the endpoint deleted the key, that's "delete, then commit" again. That's why the commit belongs in the service, followed by the invalidation.

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "If the code deletes the cache key first and commits the database change a few milliseconds later, the worst case is a few milliseconds of stale reads.", "answer": false,
  "explanation": "A reader in that gap re-caches the old value with a fresh TTL, so the worst case is stale for the whole TTL (300 s in the demo), not a few milliseconds." }
```

## 3. The race that's left

"Commit, then delete" isn't perfect. This interleaving still leaves a stale entry:

```python
# Reader: cache miss, reads the row...
assert r.get(KEY) is None
price = reader.execute("SELECT price FROM products WHERE id = 1").fetchone()[0]
# ...and is slow (GC pause, overloaded box) before it writes the cache.
# Meanwhile the writer does everything right: commit, then delete.
writer.execute("UPDATE products SET price = 900 WHERE id = 1")
writer.commit()
r.delete(KEY)
# The reader wakes up and caches what it read before the update.
r.set(KEY, json.dumps({"price": price}), ex=300)
```

```console
$ python race2.py
db=900 cache=1000 ttl=300
```

It needs a miss, then a slow reader, then a write that completes entirely inside that slow window. That's much rarer than the delete-first bug, because a read is usually far faster than a write plus commit, but under load it happens. What bounds it is the **TTL**: the redis.io guide calls the TTL "the upper bound on how long a stale value can be served".

Options when that bound isn't good enough, from cheap to expensive:

1. **Shorter TTL** for that data.
2. **Delayed second delete**: delete again shortly after the commit, to catch a slow reader's late write.
3. **Version the value**: store a version number with the row and in the cache, and refuse to cache an older version (needs an atomic compare in Redis, typically a Lua script; not runnable on this machine's fakeredis).
4. **Don't cache it.** If a decision must be correct, read the database (L01 section 4).

```quiz
{ "id": "q3", "type": "output",
  "prompt": "A reader and a writer interleave as shown. What does this print?",
  "code": "import fakeredis\n\nr = fakeredis.FakeRedis(decode_responses=True)\ndb = {\"plan\": \"free\"}\n\nseen = db[\"plan\"]          # reader: miss, reads the DB\ndb[\"plan\"] = \"pro\"         # writer: update + commit\nr.delete(\"cache:plan\")     # writer: invalidate after commit\nr.set(\"cache:plan\", seen, ex=60)   # reader: late cache fill\n\nprint(db[\"plan\"], r.get(\"cache:plan\"))",
  "answer": "pro free",
  "explanation": "The writer did everything in the right order, but the reader's late SET put back the value it read before the commit. Only the TTL (60 s here) ends the staleness." }
```

## 4. When the delete fails

The commit succeeded, then `r.delete(key)` raises because Redis is unreachable. What now?

- **Don't roll back or report failure.** The change is committed. Telling the client "failed" invites a retry of something that already happened.
- **Don't swallow it either.** `except Exception: pass` (the Python twin of `authors, _ :=`) hides two things: the stale entry, and any genuine bug in that block.
- **Catch the Redis error class, log the key, rely on the TTL.** redis-py's errors share the base class `redis.RedisError`, and its `ConnectionError` is a subclass of it.

fakeredis can simulate the outage (its docs: set the server's `connected` attribute to `False`):

```python
server = fakeredis.FakeServer()
r = fakeredis.FakeRedis(server=server, decode_responses=True)
server.connected = False
r.delete("cache:product:1")   # redis.exceptions.ConnectionError: FakeRedis is emulating a connection error.
```

If even TTL-bounded staleness is unacceptable after a failed delete, write the invalidation into the database in the same transaction as the change, and let a worker retry it until Redis is back. That's the outbox pattern, coming in ARCH.M03.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "After a committed update, `r.delete(key)` raises `redis.exceptions.ConnectionError`. Which handling is best for a profile cache with TTL 300?",
  "options": ["Roll back the update and return 503", "`except Exception: pass`", "`except redis.RedisError:` log a warning naming the key, return success; the TTL bounds staleness to 300 s", "Retry the delete in a `while True` loop until it works"], "answer": 2,
  "explanation": "The write is done, so report success. Log the stale key so the inconsistency is visible. An unbounded retry loop would hang the request for the whole Redis outage." }
```

## 5. Invalidating more than one key

Real data is cached in more than one shape. Changing product 7's price can make several keys wrong: `cache:product:7`, `cache:category:3:products` and `cache:homepage:deals`. Before you cache a new shape, write down **which writes invalidate it**. If you can't name the keys a write must delete, that shape is a poor cache candidate (or it needs a short TTL and no explicit invalidation).

```quiz
{ "id": "q5", "type": "explain", "label": "Design review",
  "prompt": "A PR caches `cache:user:{id}` and also `cache:team:{team_id}:members` (the member list with names and emails). `update_email` deletes only `cache:user:{id}`. Review it.",
  "model": "The team member list embeds the email too, so after an email change the team page shows the old email until that key's TTL expires. Either delete every key that contains the user's data (the write path must know the user's team ids), or make the list cache store only member ids and load each member through cache:user:{id}, so one invalidation covers both. Also check the order (both deletes after commit) and that a failed delete is logged.",
  "explanation": "List every cached shape that contains the changed data; each one needs an invalidation or a TTL you're willing to accept." }
```

## 6. Your turn: fix `update_email`

The exercise has a correct `get_user` and an `update_email` with three bugs from this lesson. One test checks *when* the invalidation happens by looking at the database through a second connection at the exact moment of the delete.

```exercise
ARCH.M02.L02.E1
```
