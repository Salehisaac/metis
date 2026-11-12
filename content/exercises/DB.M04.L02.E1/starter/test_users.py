import sqlite3

import pytest

import chatdb

T = "2026-11-12 10:00:00"


def load():
    import users

    return users


def names(found):
    return [u.username for u in found]


def with_tricky_names():
    conn = chatdb.make_db()
    with conn:
        conn.executemany(
            "INSERT INTO users (username, created_at) VALUES (?, ?)",
            [("50%off", T), ("500", T), ("a_b", T), ("axb", T), ("back\\slash", T), ("o'neil", T)],
        )
    return conn


def test_find_users_returns_user_objects():
    users = load()
    assert users.find_users(chatdb.make_db(), "an") == [users.User(1, "ana", "2026-10-01 10:00:00")]


def test_find_users_ignores_ascii_case_and_orders_by_username():
    users = load()
    conn = chatdb.make_db()
    assert names(users.find_users(conn, "AN")) == ["ana"]
    assert names(users.find_users(conn, "e")) == ["ben", "chen", "eli"]


def test_find_users_treats_wildcards_literally():
    users = load()
    conn = with_tricky_names()
    assert names(users.find_users(conn, "%")) == ["50%off"]
    assert names(users.find_users(conn, "_")) == ["a_b"]
    assert names(users.find_users(conn, "a_b")) == ["a_b"]
    assert names(users.find_users(conn, "\\")) == ["back\\slash"]


def test_find_users_quote_empty_and_no_match():
    users = load()
    conn = with_tricky_names()
    assert names(users.find_users(conn, "o'n")) == ["o'neil"]
    assert names(users.find_users(conn, "zzz")) == []
    assert len(users.find_users(conn, "")) == 11


def test_add_users_inserts_all_and_returns_the_count():
    users = load()
    conn = chatdb.make_db()
    assert users.add_users(conn, [("fay", T), ("gus", T)]) == 2
    assert conn.execute("SELECT id, username FROM users WHERE id > 5 ORDER BY id").fetchall() == [(6, "fay"), (7, "gus")]
    assert conn.in_transaction is False


def test_add_users_accepts_a_generator():
    users = load()
    conn = chatdb.make_db()
    assert users.add_users(conn, ((f"bot{i}", T) for i in range(3))) == 3
    assert conn.execute("SELECT count(*) FROM users").fetchone() == (8,)


def test_add_users_is_all_or_nothing():
    users = load()
    conn = chatdb.make_db()
    with pytest.raises(sqlite3.IntegrityError):
        users.add_users(conn, [("hal", T), ("ana", T)])
    assert conn.execute("SELECT count(*) FROM users").fetchone() == (5,)
    assert conn.in_transaction is False
