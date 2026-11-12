import chatdb


def run(name, params=()):
    """Run the query called `name` from chatlist.py on a fresh copy of the sample data."""
    import chatlist

    sql = getattr(chatlist, name)
    assert "select" in sql.lower(), f"write your query in chatlist.{name}"
    return chatdb.make_db().execute(sql, params).fetchall()


def test_chat_list_counts_without_fan_out():
    assert run("CHAT_LIST", (1,)) == [
        (1, "team", 3, 10, "2026-11-09 08:00:00"),
        (3, "book club", 4, 3, "2026-11-09 08:00:00"),
        (2, None, 2, 3, "2026-11-08 18:00:00"),
    ]


def test_chat_list_of_another_user():
    assert run("CHAT_LIST", (5,)) == [(3, "book club", 4, 3, "2026-11-09 08:00:00")]


def test_chat_list_with_a_chat_without_messages():
    assert run("CHAT_LIST", (4,)) == [(4, "quiet", 1, 0, None)]


def test_chat_list_puts_empty_chats_last():
    conn = chatdb.make_db()
    conn.execute("INSERT INTO chat_members (chat_id, user_id, joined_at) VALUES (4, 1, '2026-11-10 09:00:00')")
    import chatlist

    rows = conn.execute(chatlist.CHAT_LIST, (1,)).fetchall()
    assert [r[0] for r in rows] == [1, 3, 2, 4]
    assert rows[-1] == (4, "quiet", 2, 0, None)


def test_chat_list_of_unknown_user():
    assert run("CHAT_LIST", (999,)) == []


def test_latest_per_chat_breaks_ties_by_id():
    assert run("LATEST_PER_CHAT") == [
        (1, 16, "chen", "release notes"),
        (2, 12, "ana", "see you"),
        (3, 14, "ben", "joined late, hi"),
    ]


def test_latest_per_chat_after_a_new_message():
    conn = chatdb.make_db()
    conn.execute(
        "INSERT INTO messages (id, chat_id, sender_id, body, sent_at) VALUES (17, 4, 4, 'anyone?', '2026-11-10 07:00:00')"
    )
    import chatlist

    assert conn.execute(chatlist.LATEST_PER_CHAT).fetchall()[-1] == (4, 17, "dara", "anyone?")
