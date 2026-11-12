import sqlite3

import pytest

import chatdb


def load():
    import writes

    return writes


ALL_ROWS = {
    "messages": "SELECT * FROM messages ORDER BY id",
    "chat_members": "SELECT * FROM chat_members ORDER BY chat_id, user_id",
}


def all_rows(conn, table):
    return conn.execute(ALL_ROWS[table]).fetchall()


def test_add_user_gets_a_new_id():
    conn = chatdb.make_db()
    cur = conn.execute(load().ADD_USER, ("fay", "2026-11-12 10:00:00"))
    assert cur.lastrowid == 6
    assert conn.execute("SELECT id, username, created_at FROM users WHERE id = 6").fetchone() == (
        6, "fay", "2026-11-12 10:00:00",
    )


def test_add_user_duplicate_username_is_rejected():
    conn = chatdb.make_db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(load().ADD_USER, ("ana", "2026-11-12 10:00:00"))
    assert conn.execute("SELECT count(*) FROM users").fetchone() == (5,)


def test_edit_message_changes_exactly_one_row():
    conn = chatdb.make_db()
    before = all_rows(conn, "messages")
    cur = conn.execute(load().EDIT_MESSAGE, ("deploy done (v2)", "2026-11-03 17:40:00", 6))
    assert cur.rowcount == 1
    after = all_rows(conn, "messages")
    assert after[5] == (6, 1, 1, "deploy done (v2)", "2026-11-03 17:30:00", "2026-11-03 17:40:00")
    assert after[:5] + after[6:] == before[:5] + before[6:], "other messages must not change"


def test_edit_missing_message_changes_nothing():
    conn = chatdb.make_db()
    before = all_rows(conn, "messages")
    cur = conn.execute(load().EDIT_MESSAGE, ("x", "2026-11-12 10:00:00", 999))
    assert cur.rowcount == 0
    assert all_rows(conn, "messages") == before


def test_leave_chat_removes_one_membership():
    conn = chatdb.make_db()
    cur = conn.execute(load().LEAVE_CHAT, (1, 2))
    assert cur.rowcount == 1
    left = conn.execute("SELECT chat_id, user_id FROM chat_members ORDER BY chat_id, user_id").fetchall()
    assert left == [(1, 1), (1, 3), (2, 1), (2, 2), (3, 1), (3, 2), (3, 3), (3, 5), (4, 4)]


def test_leave_chat_when_not_a_member():
    conn = chatdb.make_db()
    before = all_rows(conn, "chat_members")
    cur = conn.execute(load().LEAVE_CHAT, (4, 1))
    assert cur.rowcount == 0
    assert all_rows(conn, "chat_members") == before
