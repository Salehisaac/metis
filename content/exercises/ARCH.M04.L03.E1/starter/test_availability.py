import importlib
import logging
import sys

import fakeredis
import pytest
import redis

M = 60
OPEN = 1_767_258_000            # 09:00
CLOSE = OPEN + 2 * 3600         # 11:00


def load():
    sys.modules.pop("availability", None)
    return importlib.import_module("availability")


def t(minutes_after_nine):
    return OPEN + minutes_after_nine * M


class Bookings:
    def __init__(self, rows=(), error=None):
        self.rows = list(rows)
        self.error = error
        self.calls = 0

    def __call__(self, room_id, open_ts, close_ts):
        self.calls += 1
        if self.error:
            raise self.error
        return self.rows


def test_free_slots_empty_day():
    a = load()
    assert a.free_slots([], OPEN, CLOSE) == [t(m) for m in range(0, 120, 15)]


def test_free_slots_skips_overlapping_slots():
    a = load()
    # 09:30-10:10 blocks the 09:30, 09:45 and 10:00 slots; 10:15 is free again
    assert a.free_slots([(t(30), t(70))], OPEN, CLOSE) == [t(0), t(15), t(75), t(90), t(105)]


def test_free_slots_messy_bookings():
    a = load()
    rows = [(t(105), t(200)), (t(-60), t(15)), (t(40), t(50)), (t(45), t(60))]  # unsorted, overlapping, outside
    assert a.free_slots(rows, OPEN, CLOSE) == [t(15), t(60), t(75), t(90)]


def test_free_slots_touching_and_partial_window():
    a = load()
    assert a.free_slots([(t(15), t(30))], OPEN, t(70)) == [t(0), t(30), t(45)]  # 10:00 slot would end after close
    assert a.free_slots([(OPEN, CLOSE)], OPEN, CLOSE) == []


def test_miss_then_hit():
    a = load()
    r = fakeredis.FakeRedis(decode_responses=True)
    loader = Bookings([(t(0), t(60))])
    first = a.get_availability(r, loader, 1, OPEN, CLOSE)
    second = a.get_availability(r, loader, 1, OPEN, CLOSE)
    assert first == ([t(60), t(75), t(90), t(105)], "db")
    assert second == (first[0], "cache")
    assert loader.calls == 1
    assert 0 < r.ttl(a.availability_key(1, OPEN)) <= a.AVAIL_TTL


def test_fully_booked_day_is_cached_too():
    a = load()
    r = fakeredis.FakeRedis(decode_responses=True)
    loader = Bookings([(OPEN, CLOSE)])
    a.get_availability(r, loader, 1, OPEN, CLOSE)
    assert a.get_availability(r, loader, 1, OPEN, CLOSE) == ([], "cache")
    assert loader.calls == 1


def test_redis_down_degrades_to_database(caplog):
    a = load()
    server = fakeredis.FakeServer()
    r = fakeredis.FakeRedis(server=server, decode_responses=True)
    server.connected = False
    with caplog.at_level(logging.WARNING, logger="availability"):
        got = a.get_availability(r, Bookings(), 1, OPEN, CLOSE)
    assert got == ([t(m) for m in range(0, 120, 15)], "db-degraded")
    assert any(rec.name == "availability" and rec.levelno >= logging.WARNING for rec in caplog.records)


def test_redis_write_failure_degrades(caplog):
    a = load()

    class ReadOnly(fakeredis.FakeRedis):
        def set(self, *args, **kwargs):
            raise redis.exceptions.ConnectionError("lost connection during SET")

    with caplog.at_level(logging.WARNING, logger="availability"):
        got = a.get_availability(ReadOnly(decode_responses=True), Bookings(), 1, OPEN, CLOSE)
    assert got[1] == "db-degraded"
    assert caplog.records, "log the failed cache write"


def test_database_errors_propagate():
    a = load()
    server = fakeredis.FakeServer()
    r = fakeredis.FakeRedis(server=server, decode_responses=True)
    server.connected = False
    with pytest.raises(TimeoutError):
        a.get_availability(r, Bookings(error=TimeoutError("db")), 1, OPEN, CLOSE)
