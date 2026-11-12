"""Tests for the users API. Don't edit this file: fix app.py."""

import inspect

import app as api


def test_create_user(client):
    response = client.post("/users", json={"username": "ali"})

    assert response.status_code == 201
    assert response.json() == {"id": 1, "username": "ali"}


def test_duplicate_username_is_409(client):
    client.post("/users", json={"username": "ali"})

    response = client.post("/users", json={"username": "ali"})

    assert response.status_code == 409


def test_app_still_works_after_a_duplicate(client):
    client.post("/users", json={"username": "ali"})
    client.post("/users", json={"username": "ali"})

    response = client.post("/users", json={"username": "sara"})

    assert response.status_code == 201
    assert [u["username"] for u in client.get("/users").json()] == ["ali", "sara"]


def test_no_connection_held_after_requests(client, connections):
    client.post("/users", json={"username": "ali"})
    client.get("/users")

    assert connections.checkouts > 0
    assert connections.checked_out() == 0, "a request finished but kept its connection"


def test_get_session_is_a_yield_dependency():
    assert inspect.isgeneratorfunction(api.get_session), "get_session should yield the session"
