"""YOUR tests for membership.leave_chat. test_meta.py runs them against five buggy versions.

Rules (so test_meta.py can run your tests against the buggy versions):
- keep `import membership` and call it as membership.leave_chat(...), not via `from membership import ...`
- a test function may take the `tmp_path` fixture and nothing else
"""

import sqlite3

import pytest

import chatdb
import membership

NOW = "2026-11-12 10:00:00"


def test_leaving_removes_membership_and_posts_a_message():
    conn = chatdb.make_db()
    membership.leave_chat(conn, 1, 2, NOW)
    assert conn.execute("SELECT 1 FROM chat_members WHERE chat_id = 1 AND user_id = 2").fetchone() is None
    last = conn.execute("SELECT sender_id, body FROM messages WHERE chat_id = 1 ORDER BY id DESC LIMIT 1").fetchone()
    assert last == (2, "left the chat")


def snapshot(conn):
    """Everything leave_chat could touch, in a comparable form."""
    return (
        conn.execute("SELECT * FROM chat_members ORDER BY chat_id, user_id").fetchall(),
        conn.execute("SELECT * FROM messages ORDER BY id").fetchall(),
    )


def test_success_is_committed(tmp_path):
    path = tmp_path / "chat.db"
    conn = chatdb.make_file_db(path)
    membership.leave_chat(conn, 1, 2, NOW)
    assert conn.in_transaction is False
    other = sqlite3.connect(path)
    assert other.execute("SELECT 1 FROM chat_members WHERE chat_id = 1 AND user_id = 2").fetchone() is None
    assert other.execute("SELECT count(*) FROM messages WHERE body = 'left the chat'").fetchone() == (1,)


def test_non_member_raises_and_leaves_nothing(tmp_path):
    path = tmp_path / "chat.db"
    conn = chatdb.make_file_db(path)
    other = sqlite3.connect(path)
    before = snapshot(other)
    with pytest.raises(membership.NotAMember):
        membership.leave_chat(conn, 4, 1, NOW)  # ana isn't in chat 4
    assert snapshot(conn) == before, "this connection still sees uncommitted changes"
    assert conn.in_transaction is False, "the failed transaction was left open"
    assert snapshot(other) == before, "a half-done leave was committed"


def test_other_memberships_are_untouched():
    conn = chatdb.make_db()
    membership.leave_chat(conn, 1, 2, NOW)
    assert conn.execute("SELECT chat_id FROM chat_members WHERE user_id = 2 ORDER BY chat_id").fetchall() == [
        (2,), (3,),
    ]
    assert conn.execute("SELECT count(*) FROM chat_members WHERE chat_id = 1").fetchone() == (2,)
