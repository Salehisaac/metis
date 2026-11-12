import chatdb


def run(name, params=()):
    """Run the query called `name` from outer.py on a fresh copy of the sample data."""
    import outer

    sql = getattr(outer, name)
    assert "select" in sql.lower(), f"write your query in outer.{name}"
    return chatdb.make_db().execute(sql, params).fetchall()


def test_messages_per_user_includes_zero():
    assert run("MESSAGES_PER_USER") == [("ana", 6), ("ben", 5), ("chen", 4), ("eli", 1), ("dara", 0)]


def test_silent_members_of_book_club():
    # ana joined chat 3 but only ever wrote in chats 1 and 2
    assert run("SILENT_MEMBERS", (3,)) == [("ana",)]


def test_silent_members_of_quiet_chat():
    assert run("SILENT_MEMBERS", (4,)) == [("dara",)]


def test_no_silent_members():
    assert run("SILENT_MEMBERS", (1,)) == []


def test_chat_activity_keeps_chats_without_messages():
    assert run("CHAT_ACTIVITY_SINCE", ("2026-11-08",)) == [(1, 4), (2, 1), (3, 1), (4, 0)]


def test_chat_activity_late():
    assert run("CHAT_ACTIVITY_SINCE", ("2026-11-09",)) == [(1, 2), (2, 0), (3, 1), (4, 0)]


def test_chat_activity_in_the_future():
    assert run("CHAT_ACTIVITY_SINCE", ("2027-01-01",)) == [(1, 0), (2, 0), (3, 0), (4, 0)]
