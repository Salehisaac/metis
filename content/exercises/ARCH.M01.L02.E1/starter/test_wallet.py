import importlib
import sqlite3
import sys

import pytest


def load():
    sys.modules.pop("wallet", None)
    return importlib.import_module("wallet")


def make(path=":memory:", balances=((1, 100), (2, 0))):
    w = load()
    conn = sqlite3.connect(path)
    conn.execute(w.SCHEMA)
    conn.executemany("INSERT INTO accounts VALUES (?, ?)", balances)
    conn.commit()
    return w, conn


def balances(conn):
    return dict(conn.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall())


def test_repo_does_not_commit():
    w, conn = make()
    w.AccountRepo(conn).deposit(1, 5)
    conn.rollback()
    assert balances(conn)[1] == 100, "a repository method committed on its own"


def test_withdraw_is_conditional():
    w, conn = make()
    repo = w.AccountRepo(conn)
    assert repo.withdraw(1, 101) is False
    assert balances(conn)[1] == 100
    assert repo.withdraw(1, 100) is True
    assert balances(conn)[1] == 0
    assert repo.withdraw(99, 1) is False


def test_uow_commits_on_success(tmp_path):
    w, conn = make(str(tmp_path / "w.db"))
    with w.UnitOfWork(conn) as uow:
        uow.accounts.deposit(2, 7)
    other = sqlite3.connect(str(tmp_path / "w.db"))
    assert balances(other)[2] == 7, "another connection must see the committed change"


def test_uow_rolls_back_and_reraises():
    w, conn = make()
    with pytest.raises(RuntimeError, match="boom"), w.UnitOfWork(conn) as uow:
        uow.accounts.deposit(2, 7)
        raise RuntimeError("boom")
    assert balances(conn) == {1: 100, 2: 0}


def test_transfer_moves_money():
    w, conn = make()
    w.transfer(conn, 1, 2, 30)
    w.transfer(conn, 1, 2, 70)
    assert balances(conn) == {1: 0, 2: 100}


def test_transfer_insufficient_funds_changes_nothing():
    w, conn = make()
    with pytest.raises(w.InsufficientFunds):
        w.transfer(conn, 1, 2, 101)
    assert balances(conn) == {1: 100, 2: 0}


def test_transfer_to_missing_account_changes_nothing():
    w, conn = make()
    with pytest.raises(w.AccountNotFound):
        w.transfer(conn, 1, 99, 10)
    assert balances(conn) == {1: 100, 2: 0}


def test_transfer_from_missing_account():
    w, conn = make()
    with pytest.raises(w.AccountNotFound):
        w.transfer(conn, 99, 1, 10)
    assert balances(conn) == {1: 100, 2: 0}


def test_transfer_rejects_bad_input():
    w, conn = make()
    for args in [(1, 2, 0), (1, 2, -5), (1, 1, 10)]:
        with pytest.raises(ValueError):
            w.transfer(conn, *args)
    assert balances(conn) == {1: 100, 2: 0}
