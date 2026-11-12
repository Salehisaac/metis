"""Tests for passwords.py. Don't edit this file.

The autouse fixture lowers the scrypt cost so the suite runs in milliseconds;
your code must read N, R and P from the module when it's called.
"""

import inspect

import pytest

import passwords


@pytest.fixture(autouse=True)
def cheap_cost(monkeypatch):
    monkeypatch.setattr(passwords, "N", 2**10)


def parts(stored):
    return stored.split("$")


def test_hash_has_the_documented_format():
    stored = passwords.hash_password("correct horse")

    name, n, r, p, salt, key = parts(stored)
    assert (name, int(n), int(r), int(p)) == ("scrypt", 2**10, 8, 1)
    assert len(bytes.fromhex(salt)) == 16
    assert len(bytes.fromhex(key)) == 32


def test_hash_does_not_contain_the_password():
    assert "correct horse" not in passwords.hash_password("correct horse")


def test_same_password_gets_different_salts_and_hashes():
    first = passwords.hash_password("correct horse")
    second = passwords.hash_password("correct horse")

    assert parts(first)[4] != parts(second)[4]
    assert first != second


def test_verify_correct_password():
    stored = passwords.hash_password("correct horse")

    assert passwords.verify_password("correct horse", stored) is True


@pytest.mark.parametrize("attempt", ["correct horse ", "Correct horse", "", "correct"],
                         ids=["trailing-space", "capitalised", "empty", "prefix"])
def test_verify_wrong_password(attempt):
    stored = passwords.hash_password("correct horse")

    assert passwords.verify_password(attempt, stored) is False


def test_unicode_password_round_trip():
    stored = passwords.hash_password("pässwörd 🔑")

    assert passwords.verify_password("pässwörd 🔑", stored) is True
    assert passwords.verify_password("passwörd 🔑", stored) is False


def test_old_hash_still_verifies_after_cost_increase(monkeypatch):
    stored = passwords.hash_password("correct horse")
    monkeypatch.setattr(passwords, "N", 2**11)

    assert passwords.verify_password("correct horse", stored) is True
    assert passwords.needs_rehash(stored) is True
    assert passwords.needs_rehash(passwords.hash_password("correct horse")) is False


@pytest.mark.parametrize("stored", [
    "",
    "plaintext-password",
    "md5$1024$8$1$00$00",
    "scrypt$abc$8$1$00112233445566778899aabbccddeeff$00",
    "scrypt$1024$8$1$not-hex$00",
    "scrypt$1024$8$1",
], ids=["empty", "plaintext", "other-algorithm", "n-not-a-number", "salt-not-hex", "too-few-fields"])
def test_malformed_stored_hash_is_false_not_an_exception(stored):
    assert passwords.verify_password("correct horse", stored) is False
    assert passwords.needs_rehash(stored) is True


def test_too_long_password():
    with pytest.raises(ValueError):
        passwords.hash_password("x" * 1025)
    stored = passwords.hash_password("x" * 1024)
    assert passwords.verify_password("x" * 1024, stored) is True
    assert passwords.verify_password("x" * 1025, stored) is False


def test_keys_are_compared_in_constant_time():
    assert "compare_digest" in inspect.getsource(passwords.verify_password)
