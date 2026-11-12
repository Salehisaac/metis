import pytest

import chatdb

ALL_USERS = [(1, "ana"), (2, "ben"), (3, "chen"), (4, "dara"), (5, "eli")]


def load():
    import search

    return search


def users_table_intact(conn):
    return conn.execute("SELECT id, username FROM users ORDER BY id").fetchall() == ALL_USERS


def test_find_user():
    assert load().find_user(chatdb.make_db(), "chen") == (3, "chen", "2026-10-03 09:00:00")


def test_find_user_with_a_quote_in_the_name():
    conn = chatdb.make_db()
    conn.execute("INSERT INTO users (id, username, created_at) VALUES (6, ?, ?)", ("o'neil", "2026-11-12 10:00:00"))
    assert load().find_user(conn, "o'neil") == (6, "o'neil", "2026-11-12 10:00:00")


@pytest.mark.parametrize("payload", [
    "x' OR '1'='1",
    "x' UNION SELECT id, body, sent_at FROM messages --",
], ids=["or_true", "union"])
def test_find_user_injection_finds_nothing(payload):
    assert load().find_user(chatdb.make_db(), payload) is None


def test_recent_messages():
    assert load().recent_messages(chatdb.make_db(), 2, 2) == [(12, "see you"), (5, "sure")]


def test_recent_messages_injection_in_chat_id():
    conn = chatdb.make_db()
    assert load().recent_messages(conn, "4 OR 1=1", 50) == []


def test_list_users_by_username():
    search = load()
    conn = chatdb.make_db()
    assert search.list_users(conn) == ALL_USERS
    assert search.list_users(conn, "username", "desc") == ALL_USERS[::-1]


def test_list_users_by_join_date():
    search = load()
    conn = chatdb.make_db()
    assert [r[0] for r in search.list_users(conn, "joined", "asc")] == [1, 2, 3, 5, 4]
    assert [r[0] for r in search.list_users(conn, "joined", "desc")] == [4, 5, 3, 2, 1]


@pytest.mark.parametrize("sort, direction", [
    ("id", "asc"),
    ("username; DROP TABLE users", "asc"),
    ("username", "sideways"),
    ("username", "asc; DELETE FROM users"),
], ids=["id_column", "stacked_drop", "bad_direction", "direction_injection"])
def test_list_users_rejects_anything_not_allowed(sort, direction):
    conn = chatdb.make_db()
    with pytest.raises(ValueError):
        load().list_users(conn, sort, direction)
    assert users_table_intact(conn)


def test_users_by_ids():
    assert load().users_by_ids(chatdb.make_db(), [3, 1, 99]) == [(1, "ana"), (3, "chen")]


def test_users_by_one_id_and_by_none():
    search = load()
    conn = chatdb.make_db()
    assert search.users_by_ids(conn, [2]) == [(2, "ben")]
    assert search.users_by_ids(conn, []) == []


def test_users_by_ids_injection():
    conn = chatdb.make_db()
    assert load().users_by_ids(conn, ["0) OR (1=1"]) == []
