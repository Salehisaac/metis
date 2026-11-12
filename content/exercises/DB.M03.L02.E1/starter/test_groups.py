import sqlite3

import pytest

import chatdb

NOW = "2026-11-12 10:00:00"


def setup(tmp_path):
    """The function's connection, plus a second connection that only sees committed data."""
    path = tmp_path / "chat.db"
    conn = chatdb.make_file_db(path)
    other = sqlite3.connect(path)
    return conn, other


def create(*args):
    import groups

    return groups.create_group_chat(*args)


def counts(conn):
    return tuple(
        conn.execute(sql).fetchone()[0]
        for sql in (
            "SELECT count(*) FROM chats",
            "SELECT count(*) FROM chat_members",
            "SELECT count(*) FROM messages",
        )
    )


BEFORE = (4, 10, 16)  # chats, memberships, messages in the sample data


def test_creates_chat_members_and_first_message(tmp_path):
    conn, other = setup(tmp_path)
    chat_id = create(conn, "weekend", 1, [2, 3], NOW)
    assert chat_id == 5
    assert other.execute("SELECT id, kind, title, created_at FROM chats WHERE id = 5").fetchone() == (
        5, "group", "weekend", NOW,
    )
    assert other.execute("SELECT user_id FROM chat_members WHERE chat_id = 5 ORDER BY user_id").fetchall() == [
        (1,), (2,), (3,),
    ]
    assert other.execute("SELECT sender_id, body, sent_at FROM messages WHERE chat_id = 5").fetchall() == [
        (1, "created the group", NOW),
    ]
    assert conn.in_transaction is False


def test_title_is_stripped(tmp_path):
    conn, other = setup(tmp_path)
    create(conn, "  weekend  ", 1, [], NOW)
    assert other.execute("SELECT title FROM chats WHERE id = 5").fetchone() == ("weekend",)


def test_repeated_ids_are_added_once(tmp_path):
    conn, other = setup(tmp_path)
    create(conn, "weekend", 1, [2, 2, 1], NOW)
    assert other.execute("SELECT user_id FROM chat_members WHERE chat_id = 5 ORDER BY user_id").fetchall() == [
        (1,), (2,),
    ]


def test_unknown_member_leaves_nothing_behind(tmp_path):
    conn, other = setup(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        create(conn, "weekend", 1, [2, 999], NOW)
    assert counts(other) == BEFORE, "another connection sees a half-created chat"
    assert counts(conn) == BEFORE, "this connection still holds uncommitted rows"
    assert conn.in_transaction is False, "the failed transaction was left open"


def test_unknown_creator_leaves_nothing_behind(tmp_path):
    conn, other = setup(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        create(conn, "weekend", 999, [1, 2], NOW)
    assert counts(other) == BEFORE
    assert counts(conn) == BEFORE


def test_blank_title_writes_nothing(tmp_path):
    conn, other = setup(tmp_path)
    with pytest.raises(ValueError):
        create(conn, "   ", 1, [2], NOW)
    assert counts(other) == BEFORE


def test_connection_still_works_after_a_failure(tmp_path):
    conn, other = setup(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        create(conn, "broken", 1, [999], NOW)
    chat_id = create(conn, "weekend", 1, [2], NOW)
    assert other.execute("SELECT title FROM chats WHERE id = ?", (chat_id,)).fetchone() == ("weekend",)
    assert counts(other) == (5, 12, 17)
