import sqlite3

import pytest


def db():
    from schema import connect
    conn = connect()
    conn.execute("INSERT INTO users (id, username) VALUES (1, 'ali'), (2, 'sara')")
    conn.execute("INSERT INTO chats (id, kind, title) VALUES (1, 'group', 'backend'), (2, 'direct', NULL)")
    conn.execute("INSERT INTO chat_members (chat_id, user_id, role) VALUES (1, 1, 'owner')")
    conn.execute("INSERT INTO chat_members (chat_id, user_id) VALUES (1, 2), (2, 1)")
    conn.commit()
    return conn


def refused(conn, sql, params=()):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql, params)


def test_connect_enables_foreign_keys():
    assert db().execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_valid_data_is_accepted():
    conn = db()
    assert conn.execute("SELECT count(*) FROM chat_members").fetchone()[0] == 3


def test_username_is_required_and_unique():
    conn = db()
    refused(conn, "INSERT INTO users (username) VALUES (NULL)")
    refused(conn, "INSERT INTO users (username) VALUES ('ali')")


def test_kind_is_required_and_limited():
    conn = db()
    refused(conn, "INSERT INTO chats (kind, title) VALUES (NULL, 'x')")
    refused(conn, "INSERT INTO chats (kind, title) VALUES ('channel', 'x')")


def test_group_needs_a_title_direct_does_not():
    conn = db()
    refused(conn, "INSERT INTO chats (kind, title) VALUES ('group', NULL)")
    conn.execute("INSERT INTO chats (kind, title) VALUES ('direct', NULL)")


def test_role_defaults_to_member_and_is_limited():
    conn = db()
    assert conn.execute("SELECT role FROM chat_members WHERE chat_id = 1 AND user_id = 2").fetchone()[0] == "member"
    refused(conn, "INSERT INTO chat_members (chat_id, user_id, role) VALUES (2, 2, 'king')")
    refused(conn, "INSERT INTO chat_members (chat_id, user_id, role) VALUES (2, 2, NULL)")


def test_membership_must_reference_existing_rows():
    conn = db()
    refused(conn, "INSERT INTO chat_members (chat_id, user_id) VALUES (99, 1)")
    refused(conn, "INSERT INTO chat_members (chat_id, user_id) VALUES (1, 99)")
    refused(conn, "INSERT INTO chat_members (chat_id, user_id) VALUES (NULL, 1)")


def test_deleting_a_chat_deletes_its_memberships():
    conn = db()
    conn.execute("DELETE FROM chats WHERE id = 1")
    assert conn.execute("SELECT chat_id, user_id FROM chat_members").fetchall() == [(2, 1)]


def test_a_member_cannot_be_deleted():
    conn = db()
    refused(conn, "DELETE FROM users WHERE id = 2")
    conn.execute("DELETE FROM chat_members WHERE user_id = 2")
    conn.execute("DELETE FROM users WHERE id = 2")
