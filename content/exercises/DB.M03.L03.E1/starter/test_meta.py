"""Checks YOUR tests in test_leave_chat.py. Don't edit this file.

Each bug_* function is leave_chat with one realistic transaction bug. A good test file has at least
one test that fails on each of them, and all its tests pass on the real leave_chat.
"""

import inspect

import pytest

import membership
from membership import NotAMember

INSERT = "INSERT INTO messages (chat_id, sender_id, body, sent_at) VALUES (?, ?, 'left the chat', ?)"
DELETE = "DELETE FROM chat_members WHERE chat_id = ? AND user_id = ?"


def bug_never_commits(conn, chat_id, user_id, now):
    """Never commits: this connection sees the change, nobody else ever will."""
    conn.execute(INSERT, (chat_id, user_id, now))
    if conn.execute(DELETE, (chat_id, user_id)).rowcount == 0:
        conn.rollback()
        raise NotAMember(user_id)


def bug_commits_message_first(conn, chat_id, user_id, now):
    """Commits the message before checking the membership: a non-member leaves a 'left the chat' message behind."""
    conn.execute(INSERT, (chat_id, user_id, now))
    conn.commit()
    with conn:
        if conn.execute(DELETE, (chat_id, user_id)).rowcount == 0:
            raise NotAMember(user_id)


def bug_no_rollback(conn, chat_id, user_id, now):
    """Raises without rolling back: the message stays pending on the connection, and the next commit keeps it."""
    conn.execute(INSERT, (chat_id, user_id, now))
    if conn.execute(DELETE, (chat_id, user_id)).rowcount == 0:
        raise NotAMember(user_id)
    conn.commit()


def bug_swallows_error(conn, chat_id, user_id, now):
    """Returns quietly for a non-member, and the with block commits the message."""
    with conn:
        conn.execute(INSERT, (chat_id, user_id, now))
        if conn.execute(DELETE, (chat_id, user_id)).rowcount == 0:
            return False
    return True


def bug_leaves_every_chat(conn, chat_id, user_id, now):
    """Deletes the user's membership in every chat, not just this one."""
    with conn:
        conn.execute(INSERT, (chat_id, user_id, now))
        if conn.execute("DELETE FROM chat_members WHERE user_id = ? OR chat_id = -1", (user_id,)).rowcount == 0:
            raise NotAMember(user_id)


BUGS = [bug_never_commits, bug_commits_message_first, bug_no_rollback, bug_swallows_error, bug_leaves_every_chat]


def _your_tests():
    import test_leave_chat

    assert not hasattr(test_leave_chat, "leave_chat"), (
        "test_leave_chat.py imports leave_chat directly; call membership.leave_chat(...) so the bugs can be swapped in"
    )
    return [(n, f) for n, f in vars(test_leave_chat).items() if n.startswith("test_") and inspect.isfunction(f)]


def _run(test, tmp_path_factory):
    params = set(inspect.signature(test).parameters)
    assert params <= {"tmp_path"}, f"{test.__name__} may only take tmp_path, not {sorted(params - {'tmp_path'})}"
    kwargs = {"tmp_path": tmp_path_factory.mktemp(test.__name__)} if params else {}
    test(**kwargs)


def test_your_tests_pass_on_the_real_function(tmp_path_factory):
    tests = _your_tests()
    assert len(tests) >= 3, "write at least 3 tests"
    for _, test in tests:
        _run(test, tmp_path_factory)


@pytest.mark.parametrize("bug", BUGS, ids=[b.__name__ for b in BUGS])
def test_your_tests_catch(bug, monkeypatch, tmp_path_factory):
    tests = _your_tests()
    monkeypatch.setattr(membership, "leave_chat", bug)
    for _, test in tests:
        try:
            _run(test, tmp_path_factory)
        except (Exception, pytest.fail.Exception):
            return  # caught: at least one of your tests fails on this bug
    pytest.fail(f"none of your tests fails on {bug.__name__}: {bug.__doc__}")
