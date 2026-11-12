"""Reference status-code tests for the messages API."""

import pytest

from app import StoreUnavailable, get_store

CASES = [
    pytest.param("POST", "/chats/1/messages", {"text": "hi"}, 201, id="send-ok"),
    pytest.param("GET", "/chats/1/messages", None, 200, id="list-ok"),
    # send: invalid and edge input
    pytest.param("POST", "/chats/1/messages", {"text": "x" * 500}, 201, id="send-500-chars"),
    pytest.param("POST", "/chats/1/messages", {"text": "x" * 501}, 422, id="send-501-chars"),
    pytest.param("POST", "/chats/1/messages", {"text": ""}, 422, id="send-empty"),
    pytest.param("POST", "/chats/1/messages", {}, 422, id="send-no-text"),
    pytest.param("POST", "/chats/9/messages", {"text": "hi"}, 404, id="send-unknown-chat"),
    # list: limit boundaries and errors
    pytest.param("GET", "/chats/1/messages?limit=1", None, 200, id="list-limit-1"),
    pytest.param("GET", "/chats/1/messages?limit=100", None, 200, id="list-limit-100"),
    pytest.param("GET", "/chats/1/messages?limit=0", None, 422, id="list-limit-0"),
    pytest.param("GET", "/chats/1/messages?limit=101", None, 422, id="list-limit-101"),
    pytest.param("GET", "/chats/2/messages", None, 200, id="list-empty-chat"),
    pytest.param("GET", "/chats/9/messages", None, 404, id="list-unknown-chat"),
    # delete
    pytest.param("DELETE", "/chats/1/messages/1", None, 204, id="delete-ok"),
    pytest.param("DELETE", "/chats/1/messages/99", None, 404, id="delete-unknown-message"),
    pytest.param("DELETE", "/chats/2/messages/1", None, 404, id="delete-message-of-other-chat"),
    pytest.param("DELETE", "/chats/9/messages/1", None, 404, id="delete-unknown-chat"),
]


@pytest.mark.parametrize("method, url, body, expected", CASES)
def test_status(client, method, url, body, expected):
    response = client.request(method, url, json=body)

    assert response.status_code == expected, response.text


def test_store_unavailable_is_503(client):
    def store_down():
        raise StoreUnavailable()

    client.app.dependency_overrides[get_store] = store_down

    response = client.get("/chats/1/messages")

    assert response.status_code == 503
    assert response.json() == {"detail": "storage unavailable, retry later"}
