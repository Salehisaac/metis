import sqlite3

import pytest

NOW = "2026-11-12 10:00:00"
REACT = "INSERT INTO reactions (message_id, user_id, emoji, created_at) VALUES (?, ?, ?, ?)"
BLOCK = "INSERT INTO blocks (blocker_id, blocked_id, created_at) VALUES (?, ?, ?)"


def db():
    import schema_ext

    return schema_ext.open_db()


def count(conn, table):
    sql = {"reactions": "SELECT count(*) FROM reactions", "blocks": "SELECT count(*) FROM blocks"}[table]
    return conn.execute(sql).fetchone()[0]


def test_foreign_keys_are_enforced():
    assert db().execute("PRAGMA foreign_keys").fetchone() == (1,)


def test_react_to_a_message():
    conn = db()
    conn.execute(REACT, (1, 2, "👍", NOW))
    assert conn.execute("SELECT message_id, user_id, emoji, created_at FROM reactions").fetchall() == [
        (1, 2, "👍", NOW),
    ]


def test_same_reaction_twice_is_rejected():
    conn = db()
    conn.execute(REACT, (1, 2, "👍", NOW))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(REACT, (1, 2, "👍", NOW))


def test_other_emoji_and_other_users_are_allowed():
    conn = db()
    conn.execute(REACT, (1, 2, "👍", NOW))
    conn.execute(REACT, (1, 2, "🎉", NOW))
    conn.execute(REACT, (1, 3, "👍", NOW))
    conn.execute(REACT, (2, 2, "👍", NOW))
    assert count(conn, "reactions") == 4


def test_reaction_needs_an_existing_message_and_user():
    conn = db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(REACT, (999, 2, "👍", NOW))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(REACT, (1, 999, "👍", NOW))
    assert count(conn, "reactions") == 0


def test_emoji_cannot_be_missing_or_empty():
    conn = db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(REACT, (1, 2, None, NOW))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(REACT, (1, 2, "", NOW))


def test_deleting_a_message_deletes_its_reactions():
    conn = db()
    conn.execute(REACT, (1, 2, "👍", NOW))
    conn.execute(REACT, (2, 1, "👍", NOW))
    conn.execute("DELETE FROM messages WHERE id = 1")
    assert conn.execute("SELECT message_id FROM reactions").fetchall() == [(2,)]


def test_block_a_user():
    conn = db()
    conn.execute(BLOCK, (1, 2, NOW))
    assert conn.execute("SELECT blocker_id, blocked_id, created_at FROM blocks").fetchall() == [(1, 2, NOW)]


def test_blocks_are_directional_and_unique():
    conn = db()
    conn.execute(BLOCK, (1, 2, NOW))
    conn.execute(BLOCK, (2, 1, NOW))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(BLOCK, (1, 2, NOW))
    assert count(conn, "blocks") == 2


def test_cannot_block_yourself():
    conn = db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(BLOCK, (3, 3, NOW))


def test_block_needs_existing_users():
    conn = db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(BLOCK, (1, 999, NOW))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(BLOCK, (999, 1, NOW))
