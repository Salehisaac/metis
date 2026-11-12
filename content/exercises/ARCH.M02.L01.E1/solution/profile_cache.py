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
