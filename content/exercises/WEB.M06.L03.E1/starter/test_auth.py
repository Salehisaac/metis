"""Tests for login and the current user. Don't edit this file: implement app.py."""

from datetime import timedelta

import jwt
import pytest

import app as api
import security
from conftest import TEST_SECRET, login

BAD_CREDENTIALS = {"detail": "Incorrect username or password"}


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_a_bearer_token(client):
    response = login(client)

    assert response.status_code == 200, response.text
    assert response.json()["token_type"] == "bearer"
    assert security.decode_access_token(response.json()["access_token"])["sub"] == "1"


def test_wrong_password_is_400(client):
    response = login(client, password="wrong")

    assert response.status_code == 400
    assert response.json() == BAD_CREDENTIALS


def test_unknown_user_gets_the_same_error(client):
    response = login(client, username="nobody")

    assert response.status_code == 400
    assert response.json() == BAD_CREDENTIALS


@pytest.mark.parametrize("username", ["ali", "nobody"])
def test_every_failed_login_runs_one_password_check(client, monkeypatch, username):
    calls = []

    def spy(password, stored):
        calls.append(stored)
        return False

    monkeypatch.setattr(api, "verify_password", spy)

    login(client, username=username, password="wrong")

    assert len(calls) == 1


def test_login_takes_form_fields_not_json(client):
    response = client.post("/auth/token", json={"username": "ali", "password": "s3cret-pass"})

    assert response.status_code == 422


def test_me_returns_the_user_without_secrets(client):
    token = login(client).json()["access_token"]

    response = client.get("/users/me", headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == {"id": 1, "username": "ali"}


def test_me_without_token_is_401(client):
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("kind", ["garbage", "other-key", "expired", "deleted-user", "sub-not-an-id"])
def test_me_with_bad_token_is_401(client, users, kind):
    token = {
        "garbage": lambda: "not-a-jwt",
        "other-key": lambda: jwt.encode({"sub": "1", "iss": "chat-auth", "aud": "chat-api", "iat": 0,
                                         "exp": 4102444800}, "x" * 32, algorithm="HS256"),
        "expired": lambda: security.create_access_token(1, expires_in=timedelta(minutes=-1)),
        "deleted-user": lambda: security.create_access_token(99),
        "sub-not-an-id": lambda: jwt.encode({"sub": "ali", "iss": "chat-auth", "aud": "chat-api", "iat": 0,
                                             "exp": 4102444800}, TEST_SECRET, algorithm="HS256"),
    }[kind]()

    response = client.get("/users/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_disabled_user_is_400_inactive(client):
    token = login(client, username="sara", password="other-pass").json()["access_token"]

    response = client.get("/users/me", headers=bearer(token))

    assert response.status_code == 400
    assert response.json() == {"detail": "Inactive user"}
