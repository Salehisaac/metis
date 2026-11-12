import sqlite3

SCHEMA = """
CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE);
CREATE TABLE chats (id INTEGER PRIMARY KEY, title TEXT NOT NULL);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES chats(id),
    sender_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO users (id, username) VALUES (1, 'ali')")
    conn.execute("INSERT INTO chats (id, title) VALUES (1, 'general')")
    conn.execute("INSERT INTO messages (chat_id, sender_id, body, created_at) VALUES (1, 1, 'hi', '2026-11-12')")
    conn.commit()
    return conn


def test_explain_primary_key_lookup():
    from plans import explain
    conn = make_db()
    assert explain(conn, "SELECT * FROM messages WHERE id = ?", (1,)) == [
        "SEARCH messages USING INTEGER PRIMARY KEY (rowid=?)"
    ]


def test_explain_returns_every_row_in_order():
    from plans import explain
    conn = make_db()
    assert explain(conn, "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at", (1,)) == [
        "SCAN messages",
        "USE TEMP B-TREE FOR ORDER BY",
    ]


def test_explain_without_params():
    from plans import explain
    conn = make_db()
    assert explain(conn, "SELECT body FROM messages WHERE id = 1") == [
        "SEARCH messages USING INTEGER PRIMARY KEY (rowid=?)"
    ]


def test_full_scans_unindexed_filter():
    from plans import full_scans
    conn = make_db()
    assert full_scans(conn, "SELECT * FROM messages WHERE sender_id = ?", (1,)) == ["messages"]


def test_full_scans_none_when_searching():
    from plans import full_scans
    conn = make_db()
    assert full_scans(conn, "SELECT * FROM users WHERE username = ?", ("ali",)) == []


def test_full_scans_uses_alias_from_plan():
    from plans import full_scans
    conn = make_db()
    sql = "SELECT c.title, m.body FROM chats c JOIN messages m ON m.chat_id = c.id WHERE m.sender_id = ?"
    scans = full_scans(conn, sql, (1,))
    assert len(scans) >= 1
    assert set(scans) <= {"c", "m"}


def test_constant_row_is_not_a_table_scan():
    from plans import full_scans
    conn = make_db()
    assert full_scans(conn, "SELECT 1 + 1") == []


def test_plan_changes_after_index_is_added():
    from plans import full_scans
    conn = make_db()
    sql = "SELECT * FROM messages WHERE sender_id = ?"
    assert full_scans(conn, sql, (1,)) == ["messages"]
    conn.execute("CREATE INDEX idx_messages_sender ON messages (sender_id)")
    assert full_scans(conn, sql, (1,)) == []


def test_explaining_a_delete_does_not_delete():
    from plans import explain, full_scans
    conn = make_db()
    explain(conn, "DELETE FROM messages WHERE sender_id = ?", (1,))
    full_scans(conn, "DELETE FROM messages WHERE sender_id = ?", (1,))
    assert conn.execute("SELECT count(*) FROM messages").fetchone()[0] == 1
