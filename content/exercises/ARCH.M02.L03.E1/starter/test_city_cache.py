import importlib
import random
import sys

import fakeredis
import pytest

PARIS = {"id": 1, "name": "Paris", "population": 2100000}


def load():
    sys.modules.pop("city_cache", None)
    return importlib.import_module("city_cache")


class Loader:
    def __init__(self, data=None, error=None):
        self.data = {1: PARIS} if data is None else data
        self.error = error
        self.calls = 0

    def __call__(self, city_id):
        self.calls += 1
        if self.error:
            raise self.error
        return self.data.get(city_id)


def client():
    return fakeredis.FakeRedis(decode_responses=True)


def test_found_city_uses_jittered_ttl():
    cc = load()
    r = client()
    assert cc.get_city(r, Loader(), 1, rng=random.Random(1)) == PARIS
    expected = cc.POSITIVE_TTL + random.Random(1).randrange(cc.JITTER)
    assert r.ttl("cache:city:1") == expected


def test_jitter_spreads_expiry():
    cc = load()
    r = client()
    data = {i: {"id": i} for i in range(1, 21)}
    rng = random.Random(7)
    for i in data:
        cc.get_city(r, Loader(data), i, rng=rng)
    ttls = {r.ttl(f"cache:city:{i}") for i in data}
    assert len(ttls) > 1, "20 keys cached together should not all expire together"
    assert all(cc.POSITIVE_TTL <= t < cc.POSITIVE_TTL + cc.JITTER for t in ttls)


def test_hit_skips_loader():
    cc = load()
    r = client()
    loader = Loader()
    cc.get_city(r, loader, 1)
    assert cc.get_city(r, loader, 1) == PARIS
    assert loader.calls == 1


def test_missing_city_hits_database_once():
    cc = load()
    r = client()
    loader = Loader()
    assert cc.get_city(r, loader, 404) is None
    assert cc.get_city(r, loader, 404) is None
    assert loader.calls == 1, "the second lookup of a missing id should be answered by the cache"


def test_negative_entry_has_short_exact_ttl():
    cc = load()
    r = client()
    cc.get_city(r, Loader(), 404, rng=random.Random(1))
    assert r.ttl("cache:city:404") == cc.NEGATIVE_TTL


def test_created_city_becomes_visible():
    cc = load()
    r = client()
    data = {}
    loader = Loader(data)
    assert cc.get_city(r, loader, 5) is None
    data[5] = {"id": 5, "name": "Yazd"}       # the city is created and committed...
    cc.on_city_created(r, 5)                  # ...and the service tells the cache
    assert cc.get_city(r, loader, 5) == {"id": 5, "name": "Yazd"}


def test_loader_error_is_not_cached():
    cc = load()
    r = client()
    with pytest.raises(ConnectionError):
        cc.get_city(r, Loader(error=ConnectionError("db down")), 1)
    assert r.exists("cache:city:1") == 0


def test_falsy_city_fields_are_a_hit():
    cc = load()
    r = client()
    ghost = {"id": 3, "name": "", "population": 0}
    loader = Loader({3: ghost})
    cc.get_city(r, loader, 3)
    assert cc.get_city(r, loader, 3) == ghost
    assert loader.calls == 1
