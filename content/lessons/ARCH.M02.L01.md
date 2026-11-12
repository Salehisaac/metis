---
{
  "id": "ARCH.M02.L01",
  "title": "Cache-aside reads with TTL",
  "difficulty": "intermediate",
  "minutes": 100,
  "prerequisites": ["ARCH.M01"],
  "objectives": [
    "Implement the cache-aside read path: check the cache, load from the source of truth on a miss, store with a TTL",
    "Use the redis-py API (get, set with ex, ttl, delete) and predict its return values, including TTL -1 and -2",
    "Choose a TTL from a staleness budget and explain what it bounds",
    "Avoid the classic read-path bugs: truthiness checks, caching errors, entries without a TTL"
  ],
  "why": "You've shipped Redis caching in Go, including Lua scripts with TTLs, but with AI writing the code. Here you write the read path yourself, in Python, and test it. Every caching decision in L02 and L03 (invalidation, stampedes, negative caching) is a change to this one function, so it has to be exactly right first.",
  "applications": [
    "Product pages, user profiles, settings: read-heavy data that changes rarely",
    "Results of slow external APIs (rates, weather, geocoding)",
    "Taking read load off a primary database without adding replicas"
  ],
  "exercises": ["ARCH.M02.L01.E1"],
  "sources": [
    {
      "title": "Redis docs: Redis cache-aside",
      "url": "https://redis.io/docs/latest/develop/use-cases/cache-aside/",
      "version": "redis.io docs (latest, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["The application reads from Redis, falls back to the primary on a miss and writes the result back", "Entries are keyed like cache:{entity}:{id} with a TTL that bounds staleness", "An in-process cache breaks across multiple stateless service instances", "When a popular key expires under concurrency, many processes query the database at once (a stampede)"]
    },
    {
      "title": "Redis docs: Redis cache-aside with redis-py",
      "url": "https://redis.io/docs/latest/develop/use-cases/cache-aside/redis-py",
      "version": "redis.io docs (latest, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["The TTL is the upper bound on how long a stale value can be served", "Shorter TTLs mean lower hit rates and more primary load; longer TTLs mean more stale reads", "Namespace cache keys when several applications share a Redis deployment"]
    },
    {
      "title": "Redis docs: SET",
      "url": "https://redis.io/docs/latest/commands/set/",
      "version": "redis.io command reference (latest)",
      "verified": "2026-11-12",
      "claims": ["EX sets an expire time in seconds", "Any previous time to live is discarded on a successful SET"]
    },
    {
      "title": "Redis docs: TTL",
      "url": "https://redis.io/docs/latest/commands/ttl/",
      "version": "redis.io command reference (latest)",
      "verified": "2026-11-12",
      "claims": ["TTL returns -2 if the key does not exist and -1 if it exists without an expire"]
    },
    {
      "title": "Redis docs: redis-py guide",
      "url": "https://redis.io/docs/latest/develop/clients/redis-py/",
      "version": "redis.io docs (latest); client installed here: redis 8.1.0",
      "verified": "2026-11-12",
      "claims": ["redis-py requires a running Redis server", "Responses are bytes unless decode_responses=True"]
    },
    {
      "title": "fakeredis documentation",
      "url": "https://fakeredis.readthedocs.io/en/latest/",
      "version": "fakeredis docs (latest); installed fakeredis 2.40.0",
      "verified": "2026-11-12",
      "claims": ["fakeredis is a pure-Python implementation of the Redis protocol that needs no server", "Each FakeRedis uses a FakeServer for state; sharing one FakeServer shares data", "Some behaviour differs from real Redis, e.g. unimplemented commands"]
    }
  ]
}
---
## 1. Cache-aside in one paragraph

Cache-aside is the pattern you already use: **the application** talks to both the cache and the database. Redis's own docs describe the flow: the application "reads from Redis on every request, falls back to the primary on a miss, and writes the result back to Redis", with each entry under a key like `cache:{entity}:{id}` and "a TTL that bounds how long stale data can be served". The database stays the source of truth. Redis holds copies that may be missing or slightly old.

Why Redis and not a Python dict? A dict lives in one process. The redis.io page puts it this way: an in-process cache "breaks across multiple stateless services: each instance warms independently, duplicates memory, and cannot be invalidated consistently". With four uvicorn workers you'd have four different caches.

**No Redis server on this machine.** The `redis` package (redis-py 8.1.0) is installed, but its docs note it "requires a running Redis server". So every example uses **fakeredis**, "a pure-Python implementation of the Redis protocol" with the same client API. You create `fakeredis.FakeRedis()` where production code creates `redis.Redis(host=..., port=6379)`, and the rest of the code is identical. fakeredis isn't Redis: some commands are missing (`EVAL`, Redis's Lua scripting, answers "unknown command" in the fakeredis installed here), and its docs list cases where results differ from real Redis. Anything that needs a real server is labelled.

## 2. The client API you need

```python
import fakeredis

r = fakeredis.FakeRedis(decode_responses=True)   # same API as redis.Redis(...)
print(r.get("cache:forecast:tehran"))             # miss: None
print(r.set("cache:forecast:tehran", '{"temp_c": 18}', ex=60))
print(r.get("cache:forecast:tehran"))
print(r.ttl("cache:forecast:tehran"), r.ttl("no-such-key"))
r.set("no-ttl", "x")
print(r.ttl("no-ttl"))
print(r.delete("cache:forecast:tehran"), r.delete("cache:forecast:tehran"))
```

```console
$ python basics.py
None
True
{"temp_c": 18}
60 -2
-1
1 0
```

- `get` returns **`None` for a missing key**. That's how you detect a miss.
- `set(..., ex=60)` stores the value with a 60-second expiry. Redis deletes the key after that.
- `ttl` returns the seconds left, **`-2` if the key doesn't exist and `-1` if it exists with no expiry** (both from the TTL command docs).
- `delete` returns how many keys it removed.
- Without `decode_responses=True`, values come back as `bytes` (`b'...'`). The redis-py guide says the same.

One rule from the SET docs catches people out: "Any previous time to live associated with the key is discarded on successful `SET` operation."

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import fakeredis\n\nr = fakeredis.FakeRedis(decode_responses=True)\nr.set(\"a\", \"1\", ex=100)\nr.set(\"b\", \"2\")\nr.set(\"a\", \"3\")\nprint(r.ttl(\"a\"), r.ttl(\"b\"), r.ttl(\"c\"))",
  "answer": "-1 -1 -2",
  "explanation": "The second SET on `a` has no `ex`, so it discards the old TTL and `a` now lives forever (-1). `b` never had one (-1). `c` doesn't exist (-2). Overwriting a cache entry without `ex` is a classic way to create immortal stale data." }
```

## 3. The read path

A forecast service calls a slow weather API. Cache-aside in front of it:

```python
import json

FORECAST_TTL = 600  # seconds: how stale a forecast may be


def get_forecast(r, city: str) -> dict:
    key = f"cache:forecast:{city.lower()}"
    cached = r.get(key)
    if cached is not None:                      # hit
        return json.loads(cached)
    forecast = fetch_forecast_from_api(city)    # miss: go to the source of truth
    r.set(key, json.dumps(forecast), ex=FORECAST_TTL)
    return forecast
```

Four lookups, "Tehran", "tehran", "Shiraz", "Tehran", with a counter in the fake API:

```console
$ python forecast.py
API calls: 2
['cache:forecast:shiraz', 'cache:forecast:tehran'] 600
```

Decisions hidden in those 8 lines:

- **The key is normalised** (`city.lower()`), so "Tehran" and "tehran" share an entry. Two spellings of one thing as two keys halves your hit rate, and it makes invalidation miss one of them.
- **JSON in, JSON out.** Redis stores strings. JSON keeps numbers, booleans and lists typed. (A Redis hash, which the redis.io guide uses, allows field updates but returns every field as a string.)
- **`is not None`**, not `if cached:`. Look at what goes wrong with truthiness once values are decoded:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "A user has 0 unread messages. What does this print?",
  "code": "import fakeredis\n\nr = fakeredis.FakeRedis(decode_responses=True)\ncalls = []\n\ndef count_unread_in_db(user_id):\n    calls.append(user_id)\n    return 0\n\ndef unread(user_id):\n    key = f\"cache:unread:{user_id}\"\n    value = r.get(key)\n    if value and int(value):\n        return int(value)\n    n = count_unread_in_db(user_id)\n    r.set(key, n, ex=60)\n    return n\n\nfor _ in range(3):\n    unread(7)\nprint(len(calls), r.get(\"cache:unread:7\"))",
  "answer": "3 0",
  "explanation": "The value 0 is cached correctly (as the string '0'), but `int(value)` is 0, which is falsy, so every call is treated as a miss and hits the database. The cache works for everyone except users with nothing unread. Check `value is not None`." }
```

**Common mistakes on the read path:**

- Caching an error or a half-built object. Only a real answer from the source of truth goes in.
- `set` without `ex`. One missed invalidation and the copy is stale forever.
- Different code paths building the key differently (`profile:1` vs `cache:profile:1`). Build keys in one function.

## 4. Choosing the TTL

The redis-py guide states the trade-off plainly: the TTL "is the upper bound on how long a stale value can be served. Shorter TTLs mean lower hit rates and more primary load; longer TTLs mean higher hit rates and more stale reads between writes." So pick the TTL from the **business's staleness budget**, not from a default:

| Data | Who notices staleness? | Reasonable starting TTL |
|---|---|---|
| Product description | Almost nobody | Hours (plus invalidation on edit) |
| Price shown on a list page | Customers, but checkout re-reads the database | Minutes |
| Stock count at checkout | Everyone, immediately | Don't cache the decision; read the database |
| Feature flags | Operators toggling them | Seconds |

The rule in the last row matters most: **never make a decision that must be correct (charging, stock reservation, permissions) from a cached value.** Use the cache for display, and the database inside the transaction.

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "A product page caches price with TTL 300 s and invalidates on edit. The checkout endpoint charges the cached price. What's wrong?",
  "options": ["Nothing, invalidation keeps it fresh", "If an invalidation is missed or races, the customer is charged a price up to 5 minutes old; checkout should read the price from the database", "TTL 300 is too long for any cache", "Prices can't be stored as JSON"], "answer": 1,
  "explanation": "Invalidation makes staleness rare, not impossible (L02 shows the race). Decisions that must be correct read the source of truth; the cache serves the page." }
```

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "With cache-aside, if Redis loses all its data (a restart without persistence), the application returns wrong data until the cache is rebuilt.", "answer": false,
  "explanation": "Every read falls back to the database on a miss, so answers stay correct; they're just slower and the database load spikes while the cache warms. That load spike is the real risk (L03)." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Design review",
  "prompt": "A teammate proposes caching `GET /users/{id}/orders?page=N&sort=S` responses with the full URL as the key and a TTL of 1 day, 'because orders rarely change'. Review the proposal.",
  "model": "Problems: (1) Orders change when the user places or cancels one, so a 1-day TTL shows a missing new order for up to a day unless every write invalidates all page/sort combinations, and you can't easily enumerate those keys. (2) The key space is page x sort per user, which gives a low hit rate and a lot of memory for little benefit. (3) Order lists are per-user and usually not hot. Better: measure first; if needed, cache per-user data with a short TTL (or a version number in the key that writes bump), or cache the expensive part (the order rows by id) rather than every page shape.",
  "explanation": "Cache what is read often, changes rarely and can be invalidated with keys you can name." }
```

## 5. Your turn: cache user profiles

You'll write the read path for user profiles, with the edge cases from this lesson: falsy fields, not-found users (not cached yet), loader errors, bytes vs str clients, and a corrupt entry.

```exercise
ARCH.M02.L01.E1
```
