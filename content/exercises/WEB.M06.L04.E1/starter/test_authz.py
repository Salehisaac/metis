"""Authorization tests. Don't edit this file: fix app.py."""

import pytest

from conftest import ALI, MOD, MOD2, ROOT, SARA, auth


@pytest.mark.parametrize("actor, target, expected", [
    pytest.param(None, SARA, 401, id="anonymous"),
    pytest.param(ALI, SARA, 403, id="user-bans-user"),
    pytest.param(MOD, SARA, 200, id="moderator-bans-user"),
    pytest.param(MOD, MOD2, 403, id="moderator-bans-moderator"),
    pytest.param(MOD, ROOT, 403, id="moderator-bans-admin"),
    pytest.param(ROOT, MOD, 200, id="admin-bans-moderator"),
    pytest.param(ROOT, ROOT, 403, id="admin-bans-self"),
    pytest.param(ROOT, 99, 404, id="admin-bans-unknown"),
])
def test_ban(client, store, actor, target, expected):
    response = client.post(f"/admin/users/{target}/ban", headers=auth(actor))

    assert response.status_code == expected, response.text
    if target in store.users:
        assert store.users[target].banned is (expected == 200)


def test_forbidden_ban_says_why(client):
    response = client.post(f"/admin/users/{SARA}/ban", headers=auth(ALI))

    assert response.json() == {"detail": "Not enough permissions"}


def test_banned_user_is_locked_out(client):
    client.post(f"/admin/users/{SARA}/ban", headers=auth(MOD))

    assert client.get("/chats/1/messages", headers=auth(SARA)).status_code == 401


@pytest.mark.parametrize("actor, chat_id, expected", [
    pytest.param(ALI, 1, 200, id="member"),
    pytest.param(ROOT, 1, 200, id="admin-not-member"),
    pytest.param(MOD, 1, 404, id="moderator-not-member"),
    pytest.param(ALI, 2, 404, id="user-not-member"),
    pytest.param(ALI, 99, 404, id="unknown-chat"),
    pytest.param(None, 1, 401, id="anonymous"),
])
def test_list_messages(client, actor, chat_id, expected):
    response = client.get(f"/chats/{chat_id}/messages", headers=auth(actor))

    assert response.status_code == expected, response.text
    if expected == 404:
        assert response.json() == {"detail": "chat not found"}


@pytest.mark.parametrize("actor, message_id, expected", [
    pytest.param(ALI, 1, 204, id="author"),
    pytest.param(ROOT, 1, 204, id="admin"),
    pytest.param(SARA, 1, 403, id="other-member"),
    pytest.param(MOD, 1, 404, id="not-a-member"),
    pytest.param(None, 1, 401, id="anonymous"),
])
def test_delete_message(client, store, actor, message_id, expected):
    response = client.delete(f"/chats/1/messages/{message_id}", headers=auth(actor))

    assert response.status_code == expected, response.text
    assert (message_id in store.messages) is (expected != 204)
