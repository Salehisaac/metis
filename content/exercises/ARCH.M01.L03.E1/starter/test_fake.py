import importlib
import sqlite3
import sys

import pytest


def load(name):
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def sqlite_repo():
    return load("users").SqliteUserRepo(sqlite3.connect(":memory:"))


def fake_repo():
    load("users")  # fresh users module first, so fakes imports the same DuplicateEmail class
    return load("fakes").InMemoryUserRepo()


# Contract checks: each one runs against BOTH implementations.

def check_ids_count_up(repo):
    assert repo.add("a@x.io", "A") == 1
    assert repo.add("b@x.io", "B") == 2


def check_get_returns_the_user(repo):
    uid = repo.add("Ana@X.io", "Ana")
    assert repo.get_by_email("Ana@X.io") == {"id": uid, "email": "Ana@X.io", "name": "Ana"}


def check_lookup_ignores_case_but_keeps_original(repo):
    uid = repo.add("Ana@X.io", "Ana")
    assert repo.get_by_email("ana@x.io") == {"id": uid, "email": "Ana@X.io", "name": "Ana"}


def check_missing_is_none(repo):
    repo.add("a@x.io", "A")
    assert repo.get_by_email("nobody@x.io") is None


def check_duplicate_any_case_raises(repo):
    repo.add("ana@x.io", "Ana")
    with pytest.raises(sys.modules["users"].DuplicateEmail):
        repo.add("ANA@x.io", "Other")
    assert repo.add("bo@x.io", "Bo") == 2, "a failed add must not use up an id"


def check_returned_dict_is_a_copy(repo):
    repo.add("a@x.io", "A")
    got = repo.get_by_email("a@x.io")
    got["name"] = "changed by caller"
    assert repo.get_by_email("a@x.io")["name"] == "A"


CHECKS = [check_ids_count_up, check_get_returns_the_user, check_lookup_ignores_case_but_keeps_original,
          check_missing_is_none, check_duplicate_any_case_raises, check_returned_dict_is_a_copy]


def test_contract_matches_the_real_repo():
    for check in CHECKS:
        check(sqlite_repo())


def test_fake_ids_count_up():
    check_ids_count_up(fake_repo())


def test_fake_get_returns_the_user():
    check_get_returns_the_user(fake_repo())


def test_fake_lookup_ignores_case_but_keeps_original():
    check_lookup_ignores_case_but_keeps_original(fake_repo())


def test_fake_missing_is_none():
    check_missing_is_none(fake_repo())


def test_fake_duplicate_any_case_raises():
    check_duplicate_any_case_raises(fake_repo())


def test_fake_returned_dict_is_a_copy():
    check_returned_dict_is_a_copy(fake_repo())


def test_fake_satisfies_protocol():
    repo = fake_repo()
    assert isinstance(repo, sys.modules["users"].UserRepo)


def test_signup_service_with_fake():
    repo = fake_repo()
    users = sys.modules["users"]
    assert users.signup(repo, "  Sara@X.io ", " Sara ") == 1
    assert repo.get_by_email("sara@x.io") == {"id": 1, "email": "Sara@X.io", "name": "Sara"}
    with pytest.raises(ValueError):
        users.signup(repo, "not-an-email", "X")
