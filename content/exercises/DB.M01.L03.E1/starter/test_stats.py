import chatdb


def run(name, params):
    """Run the query called `name` from stats.py on a fresh copy of the sample data."""
    import stats

    sql = getattr(stats, name)
    assert "select" in sql.lower(), f"write your query in stats.{name}"
    return chatdb.make_db().execute(sql, params).fetchall()


def test_top_senders_ignores_blank_messages_and_breaks_ties():
    params = {"chat_id": 1, "start": "2026-11-02", "end": "2026-11-09", "n": 3}
    assert run("TOP_SENDERS", params) == [(1, 3), (2, 2), (3, 2)]


def test_top_senders_limits_to_n():
    params = {"chat_id": 1, "start": "2026-11-02", "end": "2026-11-09", "n": 2}
    assert run("TOP_SENDERS", params) == [(1, 3), (2, 2)]


def test_top_senders_range_includes_start_and_excludes_end():
    # 11 is sent exactly at start; 15 and 16 exactly at end
    params = {"chat_id": 1, "start": "2026-11-08 00:00:00", "end": "2026-11-09 08:00:00", "n": 10}
    assert run("TOP_SENDERS", params) == [(1, 1), (2, 1)]


def test_top_senders_other_chat():
    params = {"chat_id": 3, "start": "2026-11-01", "end": "2026-12-01", "n": 10}
    assert run("TOP_SENDERS", params) == [(2, 1), (3, 1), (5, 1)]


def test_top_senders_empty_range():
    params = {"chat_id": 1, "start": "2026-12-01", "end": "2026-12-31", "n": 5}
    assert run("TOP_SENDERS", params) == []


def test_daily_counts_with_minimum():
    assert run("DAILY_COUNTS", {"chat_id": 1, "min_messages": 2}) == [
        ("2026-11-02", 3), ("2026-11-03", 2), ("2026-11-08", 2), ("2026-11-09", 2),
    ]


def test_daily_counts_minimum_one_keeps_every_day():
    assert run("DAILY_COUNTS", {"chat_id": 2, "min_messages": 1}) == [("2026-11-02", 2), ("2026-11-08", 1)]


def test_active_chats_counts_distinct_senders():
    assert run("ACTIVE_CHATS", {"since": "2026-11-04"}) == [(1, 3, 5), (3, 3, 3), (2, 1, 1)]


def test_active_chats_late_period():
    assert run("ACTIVE_CHATS", {"since": "2026-11-09"}) == [(1, 2, 2), (3, 1, 1)]
