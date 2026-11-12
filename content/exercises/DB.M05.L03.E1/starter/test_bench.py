import sqlite3
import time

import pytest

SCHEMA = """
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.execute(SCHEMA)
    return conn


def test_best_time_calls_fn_number_times_repeat():
    from bench import best_time
    calls = []
    best_time(lambda: calls.append(1), number=4, repeat=3)
    assert len(calls) == 12


def test_best_time_is_seconds_per_call():
    from bench import best_time
    per_call = best_time(lambda: time.sleep(0.002), number=5, repeat=2)
    assert 0.002 <= per_call < 0.02


def test_best_time_rejects_zero_rounds():
    from bench import best_time
    with pytest.raises(ValueError):
        best_time(lambda: None, number=0)
    with pytest.raises(ValueError):
        best_time(lambda: None, repeat=0)


def test_seed_inserts_n_rows_in_range():
    from bench import seed_messages
    conn = make_db()
    assert seed_messages(conn, 500, chats=10) == 500
    count, low, high = conn.execute("SELECT count(*), min(chat_id), max(chat_id) FROM messages").fetchone()
    assert count == 500
    assert 1 <= low and high <= 10
    dates = [r[0] for r in conn.execute("SELECT created_at FROM messages")]
    assert all(d.startswith("2026-") and len(d) == 10 for d in dates)


def test_seed_is_deterministic():
    from bench import seed_messages
    a, b = make_db(), make_db()
    seed_messages(a, 200, chats=5, seed=3)
    seed_messages(b, 200, chats=5, seed=3)
    query = "SELECT chat_id, sender_id, body, created_at FROM messages ORDER BY id"
    assert a.execute(query).fetchall() == b.execute(query).fetchall()


def test_seed_commits():
    from bench import seed_messages
    conn = make_db()
    seed_messages(conn, 10, chats=2)
    assert not conn.in_transaction


def test_seed_zero_rows():
    from bench import seed_messages
    conn = make_db()
    assert seed_messages(conn, 0, chats=3) == 0
    assert conn.execute("SELECT count(*) FROM messages").fetchone()[0] == 0


def test_index_report_shows_scan_then_search_and_a_speedup():
    from bench import index_report, seed_messages
    conn = make_db()
    seed_messages(conn, 30_000, chats=500, seed=1)
    report = index_report(
        conn,
        "SELECT id, body FROM messages WHERE chat_id = ? ORDER BY created_at DESC LIMIT 20",
        (42,),
        "CREATE INDEX idx_messages_chat_created ON messages (chat_id, created_at)",
        number=5,
    )
    assert set(report) == {"before", "after", "plan_before", "plan_after"}
    assert report["plan_before"][0].startswith("SCAN messages")
    assert report["plan_after"] == ["SEARCH messages USING INDEX idx_messages_chat_created (chat_id=?)"]
    assert report["after"] < report["before"]


def test_index_report_leaves_the_index_in_place():
    from bench import index_report, seed_messages
    conn = make_db()
    seed_messages(conn, 100, chats=5)
    index_report(conn, "SELECT id FROM messages WHERE sender_id = ?", (7,),
                 "CREATE INDEX idx_messages_sender ON messages (sender_id)", number=1)
    names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'")]
    assert "idx_messages_sender" in names
