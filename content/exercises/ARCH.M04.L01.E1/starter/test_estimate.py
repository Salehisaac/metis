import importlib
import sys

import pytest


def load():
    sys.modules.pop("estimate", None)
    return importlib.import_module("estimate")


def test_rps_rounds_up():
    e = load()
    assert e.rps(100_000, 10) == (2, 12)       # 1.157... -> 2 ; 11.57... -> 12
    assert e.rps(86_400, 3) == (1, 3)          # exact values stay exact


def test_rps_small_and_zero_traffic():
    e = load()
    assert e.rps(1, 1) == (1, 1)               # any traffic at all is at least 1 rps
    assert e.rps(0, 5) == (0, 0)


def test_rps_rejects_bad_input():
    e = load()
    for args in [(-1, 2), (100, 0.5), (100, 0)]:
        with pytest.raises(ValueError):
            e.rps(*args)


def test_storage_bytes():
    e = load()
    assert e.storage_bytes(3_000, 200, 365 * 3) == 657_000_000
    assert e.storage_bytes(10, 3, 1, overhead=1.5) == 45
    assert e.storage_bytes(1, 1, 1, overhead=1.01) == 2   # rounded up, never down


def test_storage_bytes_rejects_bad_input():
    e = load()
    for args, kw in [((-1, 1, 1), {}), ((1, -1, 1), {}), ((1, 1, -1), {}), ((1, 1, 1), {"overhead": 0.9})]:
        with pytest.raises(ValueError):
            e.storage_bytes(*args, **kw)


def test_human_bytes_units():
    e = load()
    assert e.human_bytes(0) == "0 B"
    assert e.human_bytes(999) == "999 B"
    assert e.human_bytes(1500) == "1.5 KB"
    assert e.human_bytes(657_000_000) == "657.0 MB"
    assert e.human_bytes(2_500_000_000_000) == "2.5 TB"


def test_human_bytes_boundaries():
    e = load()
    assert e.human_bytes(1000) == "1.0 KB"
    assert e.human_bytes(1_000_000) == "1.0 MB"
    assert e.human_bytes(5_000_000_000_000_000) == "5000.0 TB"


def test_needs_cache():
    e = load()
    assert e.needs_cache(12, 2_000) is False
    assert e.needs_cache(1_200, 2_000) is True
    assert e.needs_cache(1_000, 2_000) is False   # exactly at the limit is still fine
    assert e.needs_cache(1_000, 2_000, headroom=0.4) is True
