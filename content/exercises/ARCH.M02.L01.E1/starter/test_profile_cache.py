import importlib
import sys

import fakeredis
import pytest

ANA = {"id": 1, "name": "Ana", "bio": "", "followers": 0, "tags": []}


def load():
    sys.modules.pop("profile_cache", None)
    return importlib.import_module("profile_cache")


class Loader:
    """A fake database: counts calls."""

    def __init__(self, data=None, error=None):
        self.data = {1: ANA} if data is None else data
        self.error = error
        self.calls = 0

    def __call__(self, user_id):
        self.calls += 1
        if self.error:
            raise self.error
        return self.data.get(user_id)


def test_key_format():
    pc = load()
    assert pc.profile_key(42) == "cache:profile:42"


def test_miss_loads_and_caches_with_ttl():
    pc = load()
    r = fakeredis.FakeRedis(decode_responses=True)
    loader = Loader()
    assert pc.get_profile(r, loader, 1) == ANA
    assert loader.calls == 1
    assert r.get("cache:profile:1") is not None, "the profile should be stored in the cache"
    assert 0 < r.ttl("cache:profile:1") <= pc.PROFILE_TTL, "every cache entry needs a TTL"


def test_hit_skips_loader():
    pc = load()
    r = fakeredis.FakeRedis(decode_responses=True)
    loader = Loader()
    pc.get_profile(r, loader, 1)
    assert pc.get_profile(r, loader, 1) == ANA
    assert loader.calls == 1, "a cache hit must not call the loader"


def test_falsy_fields_survive_the_round_trip():
    pc = load()
    r = fakeredis.FakeRedis(decode_responses=True)
    pc.get_profile(r, Loader(), 1)
    cached = pc.get_profile(r, Loader(data={}), 1)
    assert cached == ANA and cached["followers"] == 0 and cached["tags"] == []


def test_not_found_is_not_cached():
    pc = load()
    r = fakeredis.FakeRedis(decode_responses=True)
    loader = Loader()
    assert pc.get_profile(r, loader, 7) is None
    assert pc.get_profile(r, loader, 7) is None
    assert loader.calls == 2
    assert r.exists("cache:profile:7") == 0


def test_loader_error_propagates_and_caches_nothing():
    pc = load()
    r = fakeredis.FakeRedis(decode_responses=True)
    with pytest.raises(TimeoutError):
        pc.get_profile(r, Loader(error=TimeoutError("db timeout")), 1)
    assert r.exists("cache:profile:1") == 0


def test_works_with_a_bytes_client():
    pc = load()
    r = fakeredis.FakeRedis()  # no decode_responses: GET returns bytes
    loader = Loader()
    pc.get_profile(r, loader, 1)
    assert pc.get_profile(r, loader, 1) == ANA
    assert loader.calls == 1


def test_corrupt_entry_is_treated_as_a_miss():
    pc = load()
    r = fakeredis.FakeRedis(decode_responses=True)
    r.set("cache:profile:1", "{not json", ex=60)
    loader = Loader()
    assert pc.get_profile(r, loader, 1) == ANA
    assert loader.calls == 1
    assert pc.get_profile(r, loader, 1) == ANA
    assert loader.calls == 1, "the corrupt entry should have been overwritten"


def test_entries_are_per_user():
    pc = load()
    r = fakeredis.FakeRedis(decode_responses=True)
    loader = Loader(data={1: ANA, 2: {"id": 2, "name": "Bo"}})
    assert pc.get_profile(r, loader, 1)["name"] == "Ana"
    assert pc.get_profile(r, loader, 2)["name"] == "Bo"
    assert loader.calls == 2
