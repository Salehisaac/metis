---
{
  "id": "ARCH.M02.L03",
  "title": "Thundering herds and negative caching",
  "difficulty": "advanced",
  "minutes": 110,
  "prerequisites": ["ARCH.M02.L02"],
  "objectives": [
    "Explain a cache stampede and measure it: N concurrent misses on one key become N database loads",
    "Implement single-flight loading with SET NX PX, a re-check after winning the lock, and a bounded wait for losers",
    "Spread expiries with TTL jitter and say which failure it prevents",
    "Cache 'not found' safely: a distinguishable marker, a shorter TTL, invalidation on create, and never for errors"
  ],
  "why": "Caches fail at the edges: when a hot key expires, when bots ask for ids that don't exist, when a whole cache warms at once. These are the cases that turn a cache from a speed-up into an outage amplifier, and they're the questions a design review will ask about your caching plan.",
  "applications": [
    "Hot keys: home page, leaderboards, a viral product",
    "Endpoints that are scanned with random ids (enumeration, scrapers)",
    "Cache warm-up after a deploy, failover or flush"
  ],
  "exercises": ["ARCH.M02.L03.E1"],
  "sources": [
    {
      "title": "Redis docs: Redis cache-aside",
      "url": "https://redis.io/docs/latest/develop/use-cases/cache-aside/",
      "version": "redis.io docs (latest, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["When a popular cached key expires under high concurrency, many processes query the database for the same record at once: a cache stampede", "Mutex locks or probabilistic early refresh mitigate stampedes"]
    },
    {
      "title": "Redis docs: Redis cache-aside with redis-py",
      "url": "https://redis.io/docs/latest/develop/use-cases/cache-aside/redis-py",
      "version": "redis.io docs (latest, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Only the caller that wins SET NX loads from the primary; others poll the cache briefly", "The lock is released by a script that deletes it only if the caller's token still matches", "The lock TTL must be longer than the worst-case primary read latency", "Cache 'not found' sentinels with a short TTL, shorter than the positive entry, so new records become visible quickly"]
    },
    {
      "title": "Redis docs: SET (NX, PX and the locking pattern)",
      "url": "https://redis.io/docs/latest/commands/set/",
      "version": "redis.io command reference (latest)",
      "verified": "2026-11-12",
      "claims": ["NX sets the key only if it does not already exist", "With NX, a SET that is not performed returns a null reply", "SET resource-name anystring NX EX max-lock-time is a simple lock; the docs discourage it in favour of Redlock for stronger guarantees", "Releasing with a token-compare script avoids deleting a lock another client acquired later"]
    },
    {
      "title": "fakeredis documentation",
      "url": "https://fakeredis.readthedocs.io/en/latest/",
      "version": "fakeredis docs (latest); installed fakeredis 2.40.0",
      "verified": "2026-11-12",
      "claims": ["fakeredis acts like a Redis server without needing one; some behaviour differs from real Redis"]
    }
  ]
}
---
## 1. The stampede

The redis.io cache-aside page describes it: "When a popular cached key expires under high concurrency, dozens of processes simultaneously query the database for the same record — a cache stampede that amplifies the exact load spike caching was supposed to prevent."

Here it is with L01's read path, 20 threads arriving together on a just-expired key, and a 50 ms query:

```python
def naive_get():
    cached = r.get(KEY)
    if cached is not None:
        return json.loads(cached)
    value = load_leaderboard()          # ~50 ms
    r.set(KEY, json.dumps(value), ex=60)
    return value
```

```console
$ python stampede.py        # first line
naive:         20 loads for 20 requests
```

All 20 checked the cache within the 50 ms before anyone refilled it, so all 20 ran the expensive query. With 2,000 requests per second on that key and a 2-second query, it's thousands of identical queries at the worst possible moment. (The demo uses threads and fakeredis in one process; with real Redis the requests come from many processes, which is the same race.)

## 2. Single-flight: one loader, everyone else waits

The fix the redis.io guide uses: on a miss, try to take a short lock with `SET ... NX PX`. **Only the winner loads**, and the others wait briefly for the winner's value to appear.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import fakeredis\n\nr = fakeredis.FakeRedis(decode_responses=True)\nprint(r.set(\"lock:x\", \"a\", nx=True, px=500), r.set(\"lock:x\", \"b\", nx=True, px=500), r.get(\"lock:x\"))",
  "answer": "True None a",
  "explanation": "NX means 'only if the key doesn't exist'. The first SET creates it and returns True. The second isn't performed, so the server sends a null reply, which redis-py returns as None. The value stays 'a'. That None/True difference is how a caller knows whether it won the lock." }
```

```python
def single_flight_get():
    cached = r.get(KEY)
    if cached is not None:
        return json.loads(cached)
    token = secrets.token_hex(8)
    if r.set(LOCK, token, nx=True, px=2000):           # we won: we load
        try:
            cached = r.get(KEY)                         # re-check: someone may have just filled it
            if cached is not None:
                return json.loads(cached)
            value = load_leaderboard()
            r.set(KEY, json.dumps(value), ex=60)
            return value
        finally:
            if r.get(LOCK) == token:                    # NOT atomic; production uses a Lua script
                r.delete(LOCK)
    deadline = time.monotonic() + 2.0                   # we lost: wait for the winner's value
    while time.monotonic() < deadline:
        time.sleep(0.01)
        cached = r.get(KEY)
        if cached is not None:
            return json.loads(cached)
    return load_leaderboard()                           # winner died: fall back to the source
```

```console
$ python stampede.py        # second line (5 runs, same result each time)
single-flight: 1 load for 20 requests
```

Each line has a reason:

- **`px=2000`: the lock expires on its own.** If the winner crashes, the lock doesn't block everyone forever. The redis.io guide says the lock TTL "needs to be longer than the worst-case primary read latency", or a slow loader loses the lock midway and a second loader starts.
- **A random `token` per caller.** Release only if the lock still holds *your* token. Otherwise a slow winner whose lock already expired would delete the *next* winner's lock. The redis.io guide does the compare-and-delete in one Lua script, so nothing can happen between the compare and the delete. **fakeredis here has no Lua (`EVAL` is an unknown command), so the demo uses a non-atomic `GET` then `DELETE`. Don't ship that version.**
- **Re-check after winning.** A caller that missed just before the previous winner filled the cache can still win a fresh lock. Without the re-check it would load again.
- **Losers wait with a deadline, then fall back.** Never wait forever on someone else's work.

A note on "locks": the SET docs present `SET resource-name anystring NX EX max-lock-time` as a simple locking pattern, but they discourage it in favour of the Redlock algorithm when you need real guarantees. Stampede protection is forgiving: if two callers ever hold the lock, the cost is one extra query, not corrupted data. **Never use this kind of lock to protect money or stock.** That's the database's job (ARCH.M01.L02).

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "The winner's query takes up to 8 s on a bad day, and the lock is taken with `px=2000`. What happens on a bad day?",
  "options": ["Nothing; the other callers keep waiting for the winner", "The lock expires after 2 s, another caller wins it and starts a second query, and the waiters may give up and query too", "Redis extends the lock automatically", "The winner's SET of the value fails"], "answer": 1,
  "explanation": "The lock TTL must exceed the worst-case load time. Otherwise single-flight quietly turns back into a (smaller) stampede on exactly the days the database is slow." }
```

## 3. Jitter: don't expire together

A stampede on one key is bad. A stampede on *every* key is worse. If a deploy or a cache flush fills 50,000 keys in the same minute, all with `ex=600`, they all expire in the same minute ten minutes later, and then again ten minutes after that.

The fix is one line: add a random number of seconds to each TTL, for example `ex = 600 + rng.randrange(60)`, which spreads the expiries over a minute. Pass the random source in as a parameter (`rng=random`) so tests can use `random.Random(seed)` and assert an exact TTL.

Other mitigations, for reference:

- **Early refresh**: refresh a hot key shortly *before* it expires (the redis.io overview mentions "probabilistic early refresh"), so the key is never actually missing.
- **Warm-up**: pre-fill the hottest keys after a deploy, before traffic arrives.

## 4. Negative caching: remembering "not found"

L01's read path caches only found values. A request for a missing id is a miss every time, and bots that scan random ids send every request to the database.

The redis.io guide's advice: "cache 'not found' sentinels with a short TTL to absorb load from probing for non-existent IDs, while making sure the sentinel is shorter than the positive cache entry so a newly-created record becomes visible quickly."

The marker has to be a stored value that is distinguishable from a real record **and** from a miss:

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import json\nimport fakeredis\n\nr = fakeredis.FakeRedis(decode_responses=True)\nr.set(\"cache:city:9\", json.dumps(None), ex=30)\nraw = r.get(\"cache:city:9\")\nprint(repr(raw), json.loads(raw), raw is None)",
  "answer": "'null' None False",
  "explanation": "The key exists and holds the string 'null', so `raw is None` is False: it's a hit, not a miss. Decoding it gives None, which means 'known not to exist'. Your read path must check the raw value against None, not the decoded one." }
```

Three rules that keep negative caching from hurting you:

1. **Shorter TTL than positive entries.** The cost of a wrong "not found" is a user who can't see something that exists.
2. **Delete the key when the record is created** (after the commit). That's the same write-path rule as L02, applied to creates.
3. **Never cache a failure as "not found".** A database timeout isn't an answer. Caching it turns a 2-second blip into 30 seconds of "doesn't exist".

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "Giving 'not found' entries a longer TTL than found entries is a good way to save database load, since missing ids rarely start existing.", "answer": false,
  "explanation": "IDs that don't exist yet can be created any moment (a new product, a new user). A long negative TTL hides new records. Keep it short, and delete it on create." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Design review",
  "prompt": "A product page key gets 5,000 requests/s. The design: cache-aside, TTL 300, single-flight lock with `px=1000`, losers poll for 1 s then load themselves. The product query takes 300 ms normally and 3 s when the database is busy. Review the design for the busy case.",
  "model": "On a busy day the 3 s query outlives the 1 s lock: after 1 s another caller wins the lock and starts a second query, and the losers stop polling after 1 s and all load themselves, so the stampede comes back exactly when the database is weakest. Fixes: a lock TTL above the worst-case load (say 5 s) and a matching poll deadline; for a key this hot, refresh it before expiry (early refresh or a background refresher) so it's never missing; add TTL jitter if many such keys are filled together; and consider serving the stale value while one caller refreshes. Measure the query's p99 to pick the numbers.",
  "explanation": "Size the lock and the wait from the worst-case load time, not the average." }
```

## 5. Your turn: negative caching and jitter

You'll harden a city lookup: cache "not found" with a short exact TTL, jitter the positive TTLs with an injected random source, make new cities visible immediately, and keep failures out of the cache.

```exercise
ARCH.M02.L03.E1
```
