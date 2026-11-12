import sqlite3

SCHEMA = """
CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
CREATE TABLE chats (id INTEGER PRIMARY KEY, title TEXT NOT NULL);
CREATE TABLE chat_members (
    chat_id INTEGER NOT NULL REFERENCES chats(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    joined_at TEXT NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES chats(id),
    sender_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

# The four hot queries. Don't change them; change INDEXES.
MY_CHATS = "SELECT chat_id FROM chat_members WHERE user_id = ? ORDER BY joined_at DESC"
HISTORY_PAGE = ("SELECT id, sender_id, body, created_at FROM messages "
                "WHERE chat_id = ? AND created_at < ? ORDER BY created_at DESC LIMIT 50")
UNREAD_COUNT = "SELECT count(*) FROM messages WHERE chat_id = ? AND created_at > ?"
SENT_IN_CHAT = "SELECT count(*) FROM messages WHERE chat_id = ? AND sender_id = ?"


def make_db():
    from inbox_indexes import INDEXES
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    for ddl in INDEXES:
        conn.execute(ddl)
    return conn


def plan(conn, sql, params):
    return [row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + sql, params)]


def created_indexes(conn):
    """{index name: [columns in order]} for indexes created with CREATE INDEX."""
    result = {}
    for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'"):
        for _seq, name, _unique, origin, _partial in conn.execute(f"PRAGMA index_list({table})"):
            if origin == "c":
                result[name] = [row[2] for row in conn.execute(f"PRAGMA index_info({name})")]
    return result


def test_every_entry_is_a_create_index_statement():
    from inbox_indexes import INDEXES
    assert INDEXES, "add at least one index"
    for ddl in INDEXES:
        assert ddl.strip().upper().startswith(("CREATE INDEX", "CREATE UNIQUE INDEX")), ddl


def test_my_chats_is_a_covering_search_without_sort():
    details = plan(make_db(), MY_CHATS, (7,))
    assert any(d.startswith("SEARCH chat_members USING COVERING INDEX") for d in details), details
    assert not any("TEMP B-TREE" in d for d in details), details


def test_history_page_uses_chat_and_time_without_sort():
    details = plan(make_db(), HISTORY_PAGE, (3, "2026-11-12"))
    assert any(d.startswith("SEARCH messages") and "(chat_id=? AND created_at<?)" in d for d in details), details
    assert not any("TEMP B-TREE" in d for d in details), details


def test_unread_count_never_touches_the_table():
    details = plan(make_db(), UNREAD_COUNT, (3, "2026-11-12"))
    assert any(d.startswith("SEARCH messages USING COVERING INDEX") and "(chat_id=? AND created_at>?)" in d
               for d in details), details


def test_sent_in_chat_searches_on_both_columns():
    details = plan(make_db(), SENT_IN_CHAT, (3, 7))
    assert any(d.startswith("SEARCH messages") and "chat_id=?" in d and "sender_id=?" in d for d in details), details


def test_no_index_is_a_prefix_of_another():
    indexes = created_indexes(make_db())
    for name, cols in indexes.items():
        for other, other_cols in indexes.items():
            if name != other:
                assert other_cols[:len(cols)] != cols, f"{name} {cols} is a prefix of {other} {other_cols}"


def test_at_most_three_indexes():
    assert len(created_indexes(make_db())) <= 3


def test_queries_still_return_the_right_rows():
    conn = make_db()
    conn.execute("INSERT INTO users VALUES (1, 'ali', '2026-01-01'), (2, 'sara', '2026-01-01')")
    conn.execute("INSERT INTO chats VALUES (1, 'general'), (2, 'random')")
    conn.execute("INSERT INTO chat_members VALUES (1, 1, '2026-01-02'), (2, 1, '2026-03-01'), (1, 2, '2026-01-05')")
    conn.executemany("INSERT INTO messages (chat_id, sender_id, body, created_at) VALUES (?, ?, ?, ?)", [
        (1, 1, "a", "2026-11-01"), (1, 2, "b", "2026-11-02"), (1, 1, "c", "2026-11-03"), (2, 1, "d", "2026-11-04"),
    ])
    assert [r[0] for r in conn.execute(MY_CHATS, (1,))] == [2, 1]
    assert [r[2] for r in conn.execute(HISTORY_PAGE, (1, "2026-11-03"))] == ["b", "a"]
    assert conn.execute(UNREAD_COUNT, (1, "2026-11-01")).fetchone()[0] == 2
    assert conn.execute(SENT_IN_CHAT, (1, 1)).fetchone()[0] == 2
