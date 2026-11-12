import sqlite3

import pytest

import chatdb

NOW = "2026-11-12 10:00:00"


def make_repo(conn=None):
    import user_repo

    return user_repo, user_repo.UserRepository(conn or chatdb.make_db())


def test_get_and_by_username_return_users():
    m, repo = make_repo()
    assert repo.get(3) == m.User(3, "chen", "2026-10-03 09:00:00")
    assert repo.by_username("dara") == m.User(4, "dara", "2026-11-01 08:00:00")


def test_get_and_by_username_missing():
    m, repo = make_repo()
    assert repo.get(999) is None
    assert repo.by_username("nobody") is None
    assert repo.by_username("x' OR '1'='1") is None


def test_add_returns_the_new_user_and_commits(tmp_path):
    path = tmp_path / "chat.db"
    m, repo = make_repo(chatdb.make_file_db(path))
    assert repo.add("  fay ", NOW) == m.User(6, "fay", NOW)
    other = sqlite3.connect(path)
    assert other.execute("SELECT id, username FROM users WHERE id = 6").fetchone() == (6, "fay")


def test_add_duplicate_raises_username_taken():
    m, repo = make_repo()
    with pytest.raises(m.UsernameTaken) as info:
        repo.add("ana", NOW)
    assert isinstance(info.value.__cause__, sqlite3.IntegrityError), "use `raise ... from err` to keep the cause"
    assert repo.page(limit=100)[-1].username == "eli"
    assert repo._conn.in_transaction is False


def test_add_blank_raises_value_error():
    m, repo = make_repo()
    with pytest.raises(ValueError):
        repo.add("   ", NOW)


def test_rename():
    m, repo = make_repo()
    assert repo.rename(2, " benjamin ") == m.User(2, "benjamin", "2026-10-03 09:00:00")
    assert repo.by_username("ben") is None
    assert repo._conn.in_transaction is False


def test_rename_errors():
    m, repo = make_repo()
    with pytest.raises(m.UserNotFound):
        repo.rename(999, "ghost")
    with pytest.raises(m.UsernameTaken):
        repo.rename(2, "ana")
    with pytest.raises(ValueError):
        repo.rename(2, " ")
    assert repo.get(2).username == "ben"
    assert repo._conn.in_transaction is False


def test_page_walks_all_users_with_keyset():
    m, repo = make_repo()
    first = repo.page(limit=2)
    assert [u.username for u in first] == ["ana", "ben"]
    second = repo.page(after=first[-1].username, limit=2)
    assert [u.username for u in second] == ["chen", "dara"]
    third = repo.page(after=second[-1].username, limit=2)
    assert [u.username for u in third] == ["eli"]
    assert repo.page(after="eli", limit=2) == []


def test_page_limit_is_validated():
    m, repo = make_repo()
    for bad in (0, -1, 101):
        with pytest.raises(ValueError):
            repo.page(limit=bad)
