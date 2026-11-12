"""Tests for tokens.py. Don't edit this file: fix tokens.py."""

import base64
import inspect
import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest

import tokens

TEST_SECRET = "t" * 32


@pytest.fixture(autouse=True)
def secret_in_env(monkeypatch):
    monkeypatch.setenv("CHAT_JWT_SECRET", TEST_SECRET)


def forge(claims, key=TEST_SECRET, algorithm="HS256"):
    now = datetime.now(timezone.utc)
    base = {"sub": "42", "role": "user", "iss": "chat-auth", "aud": "chat-api",
            "iat": now, "exp": now + timedelta(minutes=5)}
    return jwt.encode({**base, **claims}, key, algorithm=algorithm)


def test_round_trip():
    claims = tokens.decode_access_token(tokens.create_access_token(42, "moderator"))

    assert (claims["sub"], claims["role"], claims["iss"], claims["aud"]) == ("42", "moderator", "chat-auth", "chat-api")
    assert claims["exp"] - claims["iat"] == 15 * 60


def test_token_is_signed_with_the_secret_from_the_environment():
    token = tokens.create_access_token(42, "user")

    assert jwt.decode(token, TEST_SECRET, algorithms=["HS256"], audience="chat-api")["sub"] == "42"


def test_secret_is_read_on_every_call(monkeypatch):
    token = tokens.create_access_token(42, "user")
    monkeypatch.setenv("CHAT_JWT_SECRET", "r" * 32)  # the secret was rotated

    with pytest.raises(jwt.InvalidTokenError):
        tokens.decode_access_token(token)


def test_missing_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("CHAT_JWT_SECRET")

    with pytest.raises(RuntimeError):
        tokens.create_access_token(42, "user")
    with pytest.raises(RuntimeError):
        tokens.decode_access_token(forge({}))


def test_short_secret_fails_closed(monkeypatch):
    monkeypatch.setenv("CHAT_JWT_SECRET", "short")

    with pytest.raises(RuntimeError):
        tokens.create_access_token(42, "user")


def test_no_hardcoded_secret_left():
    assert "dev-secret-change-me" not in inspect.getsource(tokens)


def test_tampered_payload_is_rejected():
    header, payload, signature = tokens.create_access_token(42, "user").split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=="))
    claims["role"] = "admin"
    evil = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()

    with pytest.raises(jwt.InvalidTokenError):
        tokens.decode_access_token(f"{header}.{evil}.{signature}")


@pytest.mark.parametrize("token_kind", ["other-key", "alg-none", "expired", "other-audience", "other-issuer",
                                        "no-exp", "no-sub", "garbage"])
def test_bad_tokens_are_rejected(token_kind):
    now = datetime.now(timezone.utc)
    bad = {
        "other-key": lambda: forge({}, key="x" * 32),
        "alg-none": lambda: forge({"role": "admin"}, key=None, algorithm="none"),
        "expired": lambda: forge({"iat": now - timedelta(hours=1), "exp": now - timedelta(minutes=1)}),
        "other-audience": lambda: forge({"aud": "admin-api"}),
        "other-issuer": lambda: forge({"iss": "someone-else"}),
        "no-exp": lambda: jwt.encode({"sub": "42", "iss": "chat-auth", "aud": "chat-api", "iat": now}, TEST_SECRET),
        "no-sub": lambda: jwt.encode({"iss": "chat-auth", "aud": "chat-api", "iat": now,
                                      "exp": now + timedelta(minutes=5)}, TEST_SECRET),
        "garbage": lambda: "not.a.token",
    }[token_kind]()

    with pytest.raises(jwt.InvalidTokenError):
        tokens.decode_access_token(bad)
