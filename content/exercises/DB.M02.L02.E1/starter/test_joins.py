import chatdb


def run(name, params):
    """Run the query called `name` from joins.py on a fresh copy of the sample data."""
    import joins

    sql = getattr(joins, name)
    assert "select" in sql.lower(), f"write your query in joins.{name}"
    return chatdb.make_db().execute(sql, params).fetchall()


def test_chat_transcript():
    assert run("CHAT_TRANSCRIPT", (2,)) == [(4, "ana", "lunch?"), (5, "ben", "sure"), (12, "ana", "see you")]


def test_chat_transcript_orders_ties_by_id():
    rows = run("CHAT_TRANSCRIPT", (1,))
    assert len(rows) == 10
    assert rows[-3:] == [(13, "ben", "friday release"), (15, "ana", "weekly summary"), (16, "chen", "release notes")]


def test_chat_transcript_of_empty_chat():
    assert run("CHAT_TRANSCRIPT", (4,)) == []


def test_chat_member_names():
    assert run("CHAT_MEMBER_NAMES", (3,)) == [("ana",), ("ben",), ("chen",), ("eli",)]
    assert run("CHAT_MEMBER_NAMES", (4,)) == [("dara",)]


def test_messages_by_username():
    assert run("MESSAGES_BY_USERNAME", ("chen",)) == [(3, 1), (9, 3), (10, 1), (16, 1)]


def test_messages_by_unknown_or_silent_user():
    assert run("MESSAGES_BY_USERNAME", ("nobody",)) == []
    assert run("MESSAGES_BY_USERNAME", ("dara",)) == []


def test_shared_chats():
    assert run("SHARED_CHATS", (1, 2)) == [(1,), (2,), (3,)]
    assert run("SHARED_CHATS", (5, 2)) == [(3,)]


def test_shared_chats_none_in_common():
    assert run("SHARED_CHATS", (4, 1)) == []
