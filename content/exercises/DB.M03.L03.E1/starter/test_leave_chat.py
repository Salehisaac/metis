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


# TODO: add the tests that catch the bugs. Think about:
# - Is the success really committed? Who would notice if it weren't?
# - What happens when the user isn't a member: is the error raised, and is *nothing* left behind,
#   on this connection as well as on another one?
# - Does leaving one chat touch anything else?
