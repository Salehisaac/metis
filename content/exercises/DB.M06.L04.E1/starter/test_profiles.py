import sqlite3

import pytest


def make_db(tmp_path):
    path = str(tmp_path / "app.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL, "
                 "bio TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1)")
    conn.execute("INSERT INTO users (id, username, bio) VALUES (1, 'ali', 'Go developer')")
    conn.commit()
    return path, conn


def test_get_profile(tmp_path):
    from profiles import get_profile
    _, conn = make_db(tmp_path)
    assert get_profile(conn, 1) == ("Go developer", 1)


def test_get_profile_missing_user(tmp_path):
    from profiles import get_profile
    _, conn = make_db(tmp_path)
    with pytest.raises(LookupError):
        get_profile(conn, 99)


def test_update_returns_new_version_and_saves(tmp_path):
    from profiles import get_profile, update_bio
    path, conn = make_db(tmp_path)
    assert update_bio(conn, 1, "Learning Python", 1) == 2
    assert get_profile(sqlite3.connect(path), 1) == ("Learning Python", 2)


def test_second_writer_with_stale_version_gets_conflict(tmp_path):
    from profiles import ConflictError, get_profile, update_bio
    path, _ = make_db(tmp_path)
    alice, bob = sqlite3.connect(path), sqlite3.connect(path)
    _, alice_version = get_profile(alice, 1)
    _, bob_version = get_profile(bob, 1)
    update_bio(alice, 1, "alice's bio", alice_version)
    with pytest.raises(ConflictError):
        update_bio(bob, 1, "bob's bio", bob_version)
    assert get_profile(alice, 1) == ("alice's bio", 2)


def test_retry_after_conflict_with_fresh_version(tmp_path):
    from profiles import ConflictError, get_profile, update_bio
    _, conn = make_db(tmp_path)
    update_bio(conn, 1, "first", 1)
    with pytest.raises(ConflictError):
        update_bio(conn, 1, "second", 1)
    _, fresh = get_profile(conn, 1)
    assert update_bio(conn, 1, "second", fresh) == 3


def test_saving_the_same_bio_still_bumps_version(tmp_path):
    from profiles import update_bio
    _, conn = make_db(tmp_path)
    assert update_bio(conn, 1, "Go developer", 1) == 2


def test_missing_user_is_lookup_error_not_conflict(tmp_path):
    from profiles import ConflictError, update_bio
    _, conn = make_db(tmp_path)
    with pytest.raises(LookupError) as info:
        update_bio(conn, 99, "x", 1)
    assert not isinstance(info.value, ConflictError)


def test_successful_save_is_a_single_compare_and_set(tmp_path):
    from profiles import update_bio
    _, conn = make_db(tmp_path)
    sent = []
    conn.set_trace_callback(sent.append)
    update_bio(conn, 1, "new", 1)
    conn.set_trace_callback(None)
    statements = [s.strip().upper() for s in sent if s.split()[0].upper() not in ("BEGIN", "COMMIT")]
    assert len(statements) == 1 and statements[0].startswith("UPDATE"), sent
    assert "VERSION" in statements[0].split("WHERE", 1)[1], "the WHERE clause must check the version"
