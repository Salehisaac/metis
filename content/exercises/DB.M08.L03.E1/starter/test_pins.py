import json
import sqlite3

import pytest

SCHEMA = """
CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, settings TEXT);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1))
);
"""


def db():
    from pins import PIN_INDEX
    conn = sqlite3.connect(":memory:", isolation_level=None)
    conn.executescript(SCHEMA)
    if PIN_INDEX.strip():
        conn.execute(PIN_INDEX)
    conn.executemany("INSERT INTO messages (id, chat_id, body) VALUES (?, ?, ?)",
                     [(1, 1, "a"), (2, 1, "b"), (3, 1, "c"), (4, 2, "d")])
    return conn


def pinned(conn):
    return conn.execute("SELECT chat_id, id FROM messages WHERE pinned = 1 ORDER BY chat_id").fetchall()


def test_index_allows_one_pin_per_chat():
    conn = db()
    conn.execute("UPDATE messages SET pinned = 1 WHERE id = 1")
    conn.execute("UPDATE messages SET pinned = 1 WHERE id = 4")  # another chat: fine
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE messages SET pinned = 1 WHERE id = 2")


def test_index_is_partial():
    conn = db()
    conn.executemany("INSERT INTO messages (chat_id, body) VALUES (?, ?)", [(1, "e"), (1, "f")])
    from pins import PIN_INDEX
    assert "WHERE" in PIN_INDEX.upper()


def test_pinned_lookup_uses_the_index():
    conn = db()
    plan = [r[3] for r in conn.execute(
        "EXPLAIN QUERY PLAN SELECT id FROM messages WHERE chat_id = ? AND pinned = 1", (1,))]
    assert any(d.startswith("SEARCH messages") and "uq_messages_one_pin_per_chat" in d for d in plan), plan


def test_pin_message_pins_and_switches():
    from pins import pin_message
    conn = db()
    pin_message(conn, 1)
    pin_message(conn, 4)
    assert pinned(conn) == [(1, 1), (2, 4)]
    pin_message(conn, 3)
    assert pinned(conn) == [(1, 3), (2, 4)]


def test_pin_message_twice_is_fine():
    from pins import pin_message
    conn = db()
    pin_message(conn, 2)
    pin_message(conn, 2)
    assert pinned(conn) == [(1, 2)]


def test_pin_missing_message_changes_nothing():
    from pins import pin_message
    conn = db()
    pin_message(conn, 2)
    with pytest.raises(LookupError):
        pin_message(conn, 99)
    assert pinned(conn) == [(1, 2)]
    assert not conn.in_transaction


def test_notifications_default_on():
    from pins import users_with_notifications
    conn = db()
    conn.executemany("INSERT INTO users (username, settings) VALUES (?, ?)", [
        ("sara", json.dumps({"notifications": True, "lang": "en"})),
        ("omid", json.dumps({"notifications": False})),
        ("ali", None),
        ("lena", json.dumps({"lang": "fa"})),
        ("reza", json.dumps({"notifications": False, "lang": "fa"})),
    ])
    assert users_with_notifications(conn) == ["ali", "lena", "sara"]


def test_notifications_no_users():
    from pins import users_with_notifications
    assert users_with_notifications(db()) == []
