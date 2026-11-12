"""Cache-aside for user profiles. r is a redis.Redis-compatible client (fakeredis in tests)."""
import json  # noqa: F401  (you'll need it)

PROFILE_TTL = 300  # seconds


def profile_key(user_id: int) -> str:
    """The cache key for one user's profile: 'cache:profile:<user_id>'."""
    raise NotImplementedError


def get_profile(r, load_profile, user_id: int) -> dict | None:
    """Return the profile for user_id, using the cache in front of load_profile.

    load_profile(user_id) -> dict | None is the slow source of truth (the database).
    """
    raise NotImplementedError
