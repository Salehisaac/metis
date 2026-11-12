# Reference solution

```python
"""Cache-aside for city pages, hardened against probing for missing ids and synchronized expiry."""
import json
import random

POSITIVE_TTL = 600  # seconds, for cities that exist
JITTER = 60         # add 0..JITTER-1 extra seconds to each positive TTL
NEGATIVE_TTL = 30   # seconds, for "no such city"


def city_key(city_id: int) -> str:
    return f"cache:city:{city_id}"


def get_city(r, load_city, city_id: int, rng=random) -> dict | None:
    """Return the city dict or None.

    load_city(city_id) -> dict | None is the database lookup.
    rng is anything with randrange(n) (the random module, or random.Random(seed) in tests).
    """
    key = city_key(city_id)
    raw = r.get(key)
    if raw is not None:
        return json.loads(raw)  # JSON null is a cached "not found": None, without asking the database
    city = load_city(city_id)
    if city is None:
        r.set(key, json.dumps(None), ex=NEGATIVE_TTL)
    else:
        r.set(key, json.dumps(city), ex=POSITIVE_TTL + rng.randrange(JITTER))
    return city


def on_city_created(r, city_id: int) -> None:
    """Call after a new city is committed, so a cached 'not found' doesn't hide it."""
    r.delete(city_key(city_id))
```

**Why it works**

- **JSON `null` is the "not found" marker.** A real city is always a JSON object, so `"null"` can't collide with one. And because a negative entry is a *stored* value, `r.get` returns `"null"` (not `None`), so "known missing" and "not in the cache" stay distinguishable. One `json.loads` handles both kinds of hit.
- **Negative entries get a short, fixed TTL.** The redis.io guide recommends caching "not found" sentinels "with a short TTL" that is "shorter than the positive cache entry so a newly-created record becomes visible quickly". 30 s means bots probing random ids cost one database query per id per 30 s instead of one per request.
- **`on_city_created` deletes the key.** Without it, a city created right after someone looked it up would stay invisible for up to 30 s. It runs after the commit, for the same reason as L02.
- **Jitter on positive TTLs only.** `rng.randrange(JITTER)` spreads expiries over a minute, so keys filled together (after a deploy or a cache flush) don't all expire in the same second and stampede the database together. Passing `rng` in makes the TTL predictable in tests with `random.Random(seed)`.
- **Errors aren't "not found".** If `load_city` raises, the `set` lines never run. Caching a marker on a database timeout would turn a 2-second outage into 30 seconds of "city doesn't exist".

**Alternatives**

- A separate key for negative entries (`cache:city:404:missing`) makes them easy to count and flush, at the cost of two `GET`s on a miss.
- A Bloom filter of existing ids in front of the cache rejects most probes without touching Redis. It's worth it only at very high probe rates; it needs a module or library that isn't installed here.
