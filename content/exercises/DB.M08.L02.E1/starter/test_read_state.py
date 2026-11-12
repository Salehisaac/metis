import sqlite3

SCHEMA = """
CREATE TABLE chat_members (chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, PRIMARY KEY (chat_id, user_id));
CREATE TABLE read_markers (
    chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, last_read_id INTEGER NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);
CREATE TABLE messages (id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, body TEXT NOT NULL);
"""


def db():
    conn = sqlite3.connect(":memory:", isolation_level=None)
    conn.executescript(SCHEMA)
    return conn


def traced(conn, fn, *args):
    sent = []
    conn.set_trace_callback(sent.append)
    try:
        result = fn(conn, *args)
    finally:
        conn.set_trace_callback(None)
    return result, [s.strip().upper() for s in sent if s.split()[0].upper() not in ("BEGIN", "COMMIT")]


def test_join_chat_true_then_false():
    from read_state import join_chat
    conn = db()
    assert join_chat(conn, 1, 10) is True
    assert join_chat(conn, 1, 10) is False
    assert join_chat(conn, 2, 10) is True
    assert conn.execute("SELECT count(*) FROM chat_members").fetchone()[0] == 2


def test_join_chat_is_a_single_insert():
    from read_state import join_chat
    conn = db()
    for _ in range(2):
        _, sent = traced(conn, join_chat, 1, 10)
        assert len(sent) == 1 and sent[0].startswith("INSERT"), sent


def test_mark_read_creates_and_moves_forward():
    from read_state import mark_read
    conn = db()
    assert mark_read(conn, 1, 10, 5) == 5
    assert mark_read(conn, 1, 10, 9) == 9
    assert conn.execute("SELECT last_read_id FROM read_markers").fetchall() == [(9,)]


def test_mark_read_never_moves_backwards():
    from read_state import mark_read
    conn = db()
    mark_read(conn, 1, 10, 9)
    assert mark_read(conn, 1, 10, 4) == 9
    assert mark_read(conn, 1, 10, 9) == 9
    assert conn.execute("SELECT last_read_id FROM read_markers").fetchall() == [(9,)]


def test_mark_read_is_per_chat_and_user():
    from read_state import mark_read
    conn = db()
    mark_read(conn, 1, 10, 9)
    assert mark_read(conn, 1, 20, 3) == 3
    assert mark_read(conn, 2, 10, 1) == 1


def test_mark_read_writes_with_one_upsert():
    from read_state import mark_read
    conn = db()
    mark_read(conn, 1, 10, 9)
    _, sent = traced(conn, mark_read, 1, 10, 4)
    assert sent and sent[0].startswith("INSERT") and "ON CONFLICT" in sent[0], sent


def test_delete_chat_messages_returns_sorted_ids():
    from read_state import delete_chat_messages
    conn = db()
    conn.executemany("INSERT INTO messages (id, chat_id, body) VALUES (?, ?, ?)",
                     [(7, 1, "a"), (3, 1, "b"), (5, 2, "c"), (9, 1, "d")])
    assert delete_chat_messages(conn, 1) == [3, 7, 9]
    assert conn.execute("SELECT id FROM messages").fetchall() == [(5,)]
    assert delete_chat_messages(conn, 1) == []


def test_delete_chat_messages_is_one_statement():
    from read_state import delete_chat_messages
    conn = db()
    conn.execute("INSERT INTO messages (id, chat_id, body) VALUES (1, 1, 'x')")
    _, sent = traced(conn, delete_chat_messages, 1)
    assert len(sent) == 1 and sent[0].startswith("DELETE") and "RETURNING" in sent[0], sent
