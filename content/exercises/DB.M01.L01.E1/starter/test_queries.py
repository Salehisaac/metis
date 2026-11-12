import chatdb


def run(name, params):
    """Run the query called `name` from queries.py on a fresh copy of the sample data."""
    import queries

    sql = getattr(queries, name)
    assert "select" in sql.lower(), f"write your query in queries.{name}"
    return chatdb.make_db().execute(sql, params).fetchall()


def test_unedited_by_sender():
    assert run("UNEDITED_BY_SENDER", (1,)) == [
        (1, "morning all"), (4, "lunch?"), (6, "deploy done"), (11, "thanks!"), (12, "see you"),
    ]


def test_unedited_by_sender_without_messages():
    assert run("UNEDITED_BY_SENDER", (4,)) == []


def test_latest_in_chat_breaks_ties_by_id():
    assert run("LATEST_IN_CHAT", (1, 3)) == [
        (16, "2026-11-09 08:00:00"), (15, "2026-11-09 08:00:00"), (13, "2026-11-08 18:00:00"),
    ]


def test_latest_in_chat_when_n_exceeds_rows():
    assert run("LATEST_IN_CHAT", (2, 100)) == [
        (12, "2026-11-08 18:00:00"), (5, "2026-11-02 12:00:00"), (4, "2026-11-02 12:00:00"),
    ]


def test_latest_in_empty_chat():
    assert run("LATEST_IN_CHAT", (4, 5)) == []


def test_in_chat_from_either_stays_in_the_chat():
    # user 1 also wrote in chat 2; those messages must not appear
    assert run("IN_CHAT_FROM_EITHER", (1, 2, 1)) == [(1,), (2,), (6,), (7,), (11,), (13,), (15,)]


def test_in_chat_from_either_other_chat():
    assert run("IN_CHAT_FROM_EITHER", (3, 5, 2)) == [(8,), (14,)]


def test_users_page():
    assert run("USERS_PAGE", (2, 2)) == [("chen",), ("dara",)]


def test_users_last_page_and_past_the_end():
    assert run("USERS_PAGE", (2, 4)) == [("eli",)]
    assert run("USERS_PAGE", (2, 10)) == []
