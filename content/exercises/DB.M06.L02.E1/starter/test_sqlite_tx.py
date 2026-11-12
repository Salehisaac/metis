import sqlite3

import pytest


def make_db(tmp_path):
    path = str(tmp_path / "chat.db")
    setup = sqlite3.connect(path)
    setup.execute("CREATE TABLE chats (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")
    setup.execute("INSERT INTO chats (title) VALUES ('general')")
    setup.commit()
    setup.close()
    return path


def count_chats(path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT count(*) FROM chats").fetchone()[0]
    finally:
        conn.close()


def test_connect_sets_busy_timeout(tmp_path):
    from sqlite_tx import connect
    path = make_db(tmp_path)
    assert connect(path).execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert connect(path, busy_timeout=0.25).execute("PRAGMA busy_timeout").fetchone()[0] == 250


def test_connect_has_no_implicit_transactions(tmp_path):
    from sqlite_tx import connect
    path = make_db(tmp_path)
    conn = connect(path)
    conn.execute("INSERT INTO chats (title) VALUES ('random')")
    assert not conn.in_transaction
    assert count_chats(path) == 2


def test_write_transaction_commits(tmp_path):
    from sqlite_tx import connect, write_transaction
    path = make_db(tmp_path)
    conn = connect(path)
    with write_transaction(conn):
        conn.execute("INSERT INTO chats (title) VALUES ('random')")
        conn.execute("INSERT INTO chats (title) VALUES ('jobs')")
    assert not conn.in_transaction
    assert count_chats(path) == 3


def test_write_transaction_rolls_back_and_reraises(tmp_path):
    from sqlite_tx import connect, write_transaction
    path = make_db(tmp_path)
    conn = connect(path)
    with pytest.raises(ValueError):
        with write_transaction(conn):
            conn.execute("INSERT INTO chats (title) VALUES ('random')")
            raise ValueError("boom")
    assert not conn.in_transaction
    assert count_chats(path) == 1


def test_write_lock_is_taken_at_the_start(tmp_path):
    from sqlite_tx import connect, write_transaction
    path = make_db(tmp_path)
    a, b = connect(path), connect(path, busy_timeout=0)
    with write_transaction(a):
        # a hasn't written anything yet, but must already hold the write lock
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            b.execute("BEGIN IMMEDIATE")


def test_readers_still_read_during_a_write(tmp_path):
    from sqlite_tx import connect, write_transaction
    path = make_db(tmp_path)
    a, b = connect(path), connect(path, busy_timeout=0)
    with write_transaction(a):
        a.execute("INSERT INTO chats (title) VALUES ('random')")
        assert b.execute("SELECT count(*) FROM chats").fetchone()[0] == 1


def test_lock_is_released_after_commit_and_after_rollback(tmp_path):
    from sqlite_tx import connect, write_transaction
    path = make_db(tmp_path)
    a, b = connect(path), connect(path, busy_timeout=0)
    with write_transaction(a):
        a.execute("INSERT INTO chats (title) VALUES ('random')")
    b.execute("BEGIN IMMEDIATE")
    b.execute("ROLLBACK")
    with pytest.raises(RuntimeError):
        with write_transaction(a):
            raise RuntimeError("fail")
    b.execute("BEGIN IMMEDIATE")
    b.execute("ROLLBACK")
