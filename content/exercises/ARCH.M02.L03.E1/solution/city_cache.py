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
