import sqlite3
import threading

import pytest

SCHEMA = """
CREATE TABLE chat_members (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    unread_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, user_id)
)
"""


def make_db(tmp_path):
    path = str(tmp_path / "chat.db")
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    conn.executemany("INSERT INTO chat_members (chat_id, user_id) VALUES (?, ?)",
                     [(1, 10), (1, 20), (1, 30), (2, 10)])
    conn.commit()
    return path, conn


def unread(conn, chat_id, user_id):
    return conn.execute("SELECT unread_count FROM chat_members WHERE chat_id = ? AND user_id = ?",
                        (chat_id, user_id)).fetchone()[0]


def traced(conn, fn, *args):
    """Run fn(conn, *args) and return the SQL statements it sent (without BEGIN/COMMIT)."""
    statements = []
    conn.set_trace_callback(statements.append)
    try:
        fn(conn, *args)
    finally:
        conn.set_trace_callback(None)
    return [s.strip() for s in statements if s.split()[0].upper() not in ("BEGIN", "COMMIT")]


def test_increment_adds_one(tmp_path):
    from unread import increment_unread
    _, conn = make_db(tmp_path)
    increment_unread(conn, 1, 20)
    increment_unread(conn, 1, 20)
    assert unread(conn, 1, 20) == 2
    assert unread(conn, 1, 10) == 0


def test_increment_non_member_raises(tmp_path):
    from unread import increment_unread
    _, conn = make_db(tmp_path)
    with pytest.raises(LookupError):
        increment_unread(conn, 2, 20)


def test_increment_is_one_update_statement(tmp_path):
    from unread import increment_unread
    _, conn = make_db(tmp_path)
    sent = traced(conn, increment_unread, 1, 20)
    assert len(sent) == 1, sent
    assert sent[0].upper().startswith("UPDATE"), sent


def test_increment_commits(tmp_path):
    from unread import increment_unread
    path, conn = make_db(tmp_path)
    increment_unread(conn, 1, 20)
    assert unread(sqlite3.connect(path), 1, 20) == 1


def test_fan_out_skips_sender(tmp_path):
    from unread import fan_out_unread
    _, conn = make_db(tmp_path)
    assert fan_out_unread(conn, 1, 10) == 2
    assert [unread(conn, 1, u) for u in (10, 20, 30)] == [0, 1, 1]
    assert unread(conn, 2, 10) == 0


def test_fan_out_unknown_chat_updates_nothing(tmp_path):
    from unread import fan_out_unread
    _, conn = make_db(tmp_path)
    assert fan_out_unread(conn, 99, 10) == 0


def test_fan_out_is_one_update_statement(tmp_path):
    from unread import fan_out_unread
    _, conn = make_db(tmp_path)
    sent = traced(conn, fan_out_unread, 1, 10)
    assert len(sent) == 1, sent
    assert sent[0].upper().startswith("UPDATE"), sent


def test_no_lost_updates_under_concurrency(tmp_path):
    from unread import fan_out_unread, increment_unread
    path, conn = make_db(tmp_path)
    errors = []

    def worker():
        own = sqlite3.connect(path, timeout=30)
        try:
            for _ in range(50):
                increment_unread(own, 1, 20)
                fan_out_unread(own, 1, 10)
        except Exception as e:  # report in the test, not as a thread traceback
            errors.append(e)
        finally:
            own.close()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert unread(conn, 1, 20) == 400  # 200 direct increments + 200 fan-outs
    assert unread(conn, 1, 30) == 200
