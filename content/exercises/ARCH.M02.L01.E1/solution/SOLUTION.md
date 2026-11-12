# Reference solution

```python
"""Cache-aside for user profiles. r is a redis.Redis-compatible client (fakeredis in tests)."""
import json

PROFILE_TTL = 300  # seconds


def profile_key(user_id: int) -> str:
    """The cache key for one user's profile: 'cache:profile:<user_id>'."""
    return f"cache:profile:{user_id}"


def get_profile(r, load_profile, user_id: int) -> dict | None:
    """Return the profile for user_id, using the cache in front of load_profile.

    load_profile(user_id) -> dict | None is the slow source of truth (the database).
    """
    key = profile_key(user_id)
    raw = r.get(key)
    if raw is not None:
        try:
            return json.loads(raw)
        except ValueError:
            pass  # corrupt entry: fall through, reload and overwrite it
    profile = load_profile(user_id)
    if profile is not None:
        r.set(key, json.dumps(profile), ex=PROFILE_TTL)
    return profile
```

**Why it works**

- **`is not None`, not truthiness.** `GET` returns `None` only for a missing key. Testing `if raw:` happens to work for JSON strings, but it's the wrong question, and it breaks the moment you cache a value whose encoding is empty.
- **Only real database answers go into the cache.** A `None` (user not found) isn't stored, and if `load_profile` raises, the `set` line is never reached, so there's no half-written entry. Caching "not found" on purpose (negative caching) is L03, with its own shorter TTL.
- **Every entry gets a TTL.** `ex=PROFILE_TTL` bounds how long a stale copy can be served even if an invalidation is ever missed (L02). Without it, a missed invalidation is stale forever.
- **`json.loads` takes `str` or `bytes`**, so the function works with both client configurations.
- **A corrupt entry is a miss.** `json.JSONDecodeError` is a subclass of `ValueError`. Catching exactly that (not `Exception`) means a bad cache entry heals itself on the next read, while real bugs and loader errors still surface.

**Alternatives**

- Store the profile as a Redis hash (`HSET` plus `EXPIRE`) like the redis.io guide does. It allows updating one field in place, but every value comes back as a string, so you lose JSON's types (`0` becomes `"0"`).
- `functools.lru_cache` is an in-process cache. It's fine for one process and immutable data, but each instance has its own copy and you can't invalidate it from another process.
