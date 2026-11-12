"""Tests for POST /chats. Don't edit this file: fix app.py."""

NOTHING = {"chats": 0, "members": 0, "messages": 0}


def test_create_chat_with_members_and_message(client, counts):
    body = {"title": "backend", "member_ids": [1, 2], "first_message": "welcome!"}

    response = client.post("/chats", json=body)

    assert response.status_code == 201, response.text
    assert response.json() == {"id": 1, "title": "backend", "member_ids": [1, 2]}
    assert counts() == {"chats": 1, "members": 2, "messages": 1}


def test_create_chat_without_first_message(client, counts):
    response = client.post("/chats", json={"title": "ops", "member_ids": [2]})

    assert response.status_code == 201, response.text
    assert counts() == {"chats": 1, "members": 1, "messages": 0}


def test_unknown_member_writes_nothing(client, counts):
    response = client.post("/chats", json={"title": "backend", "member_ids": [1, 99]})

    assert response.status_code == 404
    assert response.json() == {"detail": "user 99 not found"}
    assert counts() == NOTHING


def test_duplicate_title_is_409_and_writes_nothing_new(client, counts):
    client.post("/chats", json={"title": "ops", "member_ids": [1]})

    response = client.post("/chats", json={"title": "ops", "member_ids": [2], "first_message": "hi"})

    assert response.status_code == 409
    assert counts() == {"chats": 1, "members": 1, "messages": 0}


def test_duplicate_member_is_409_not_201(client, counts):
    response = client.post("/chats", json={"title": "backend", "member_ids": [1, 1]})

    assert response.status_code == 409, "the client must not be told 201 when nothing was saved"
    assert counts() == NOTHING


def test_app_works_after_a_failed_create(client, counts):
    client.post("/chats", json={"title": "backend", "member_ids": [1, 99]})

    response = client.post("/chats", json={"title": "backend", "member_ids": [1]})

    assert response.status_code == 201, response.text
    assert counts() == {"chats": 1, "members": 1, "messages": 0}
