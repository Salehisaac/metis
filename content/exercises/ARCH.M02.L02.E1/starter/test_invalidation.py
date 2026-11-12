import importlib
import logging
import sqlite3
import sys

import fakeredis
import pytest


def load():
    sys.modules.pop("users", None)
    return importlib.import_module("users")


def make_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)")
    conn.execute("INSERT INTO users VALUES (1, 'old@x.io')")
    conn.commit()
    return conn


class SpyRedis(fakeredis.FakeRedis):
    """Records, for every delete, what ANOTHER connection sees in the database at that moment."""

    observer = None  # a second sqlite3 connection, set by the test
    deletes: list

    def delete(self, *names):
        seen = self.observer.execute("SELECT email FROM users WHERE id = 1").fetchone()[0]
        self.deletes.append((names, seen))
        return super().delete(*names)


def test_get_user_is_cache_aside(tmp_path):
    users = load()
    conn = make_db(str(tmp_path / "u.db"))
    r = fakeredis.FakeRedis(decode_responses=True)
    assert users.get_user(conn, r, 1) == {"id": 1, "email": "old@x.io"}
    assert r.ttl("cache:user:1") > 0


def test_reader_sees_new_email_after_update(tmp_path):
    users = load()
    conn = make_db(str(tmp_path / "u.db"))
    r = fakeredis.FakeRedis(decode_responses=True)
    users.get_user(conn, r, 1)  # warm the cache with the old email
    users.update_email(conn, r, 1, " New@X.io ")
    assert users.get_user(conn, r, 1) == {"id": 1, "email": "new@x.io"}


def test_invalidation_happens_after_commit(tmp_path):
    users = load()
    path = str(tmp_path / "u.db")
    conn = make_db(path)
    r = SpyRedis(decode_responses=True)
    r.observer, r.deletes = sqlite3.connect(path), []
    users.update_email(conn, r, 1, "new@x.io")
    assert r.deletes, "update_email never deleted a cache key"
    names, seen = r.deletes[-1]
    assert "cache:user:1" in names
    assert seen == "new@x.io", "the cache was invalidated before the new email was committed"


def test_unknown_user_raises(tmp_path):
    users = load()
    conn = make_db(str(tmp_path / "u.db"))
    r = fakeredis.FakeRedis(decode_responses=True)
    with pytest.raises(users.UserNotFound):
        users.update_email(conn, r, 99, "a@x.io")


def test_redis_down_update_still_counts_and_is_logged(tmp_path, caplog):
    users = load()
    conn = make_db(str(tmp_path / "u.db"))
    server = fakeredis.FakeServer()
    r = fakeredis.FakeRedis(server=server, decode_responses=True)
    server.connected = False
    with caplog.at_level(logging.WARNING, logger="users"):
        users.update_email(conn, r, 1, "new@x.io")  # must not raise: the DB change is committed
    assert conn.execute("SELECT email FROM users WHERE id = 1").fetchone()[0] == "new@x.io"
    warnings = [rec for rec in caplog.records if rec.name == "users" and rec.levelno >= logging.WARNING]
    assert warnings, "a failed invalidation must be logged, not swallowed"
    assert "cache:user:1" in warnings[0].getMessage(), "say which key may now be stale"


def test_non_redis_errors_are_not_hidden(tmp_path):
    users = load()
    conn = make_db(str(tmp_path / "u.db"))

    class Broken(fakeredis.FakeRedis):
        def delete(self, *names):
            raise TypeError("a bug, not an outage")

    with pytest.raises(TypeError):
        users.update_email(conn, Broken(decode_responses=True), 1, "new@x.io")
