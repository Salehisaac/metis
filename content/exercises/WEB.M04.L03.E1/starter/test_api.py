"""YOUR status-code tests for the messages API in app.py.

1. Grow CASES: one row per request, (method, url, json_body_or_None, expected_status).
   Cover normal, invalid, edge and error paths of all three endpoints. Keep the two rows
   that are here: the exercise looks for their test ids. Every row runs on a fresh,
   seeded app (see conftest.py): chat 1 has message 1, chat 2 has no messages.
2. Write test_store_unavailable_is_503 (see its docstring).
3. test_meta.py runs your rows and tests against seven broken copies of app.py.
   Each broken copy must make at least one row or test fail.
"""

import pytest

from app import StoreUnavailable, get_store

CASES = [
    pytest.param("POST", "/chats/1/messages", {"text": "hi"}, 201, id="send-ok"),
    pytest.param("GET", "/chats/1/messages", None, 200, id="list-ok"),
]


@pytest.mark.parametrize("method, url, body, expected", CASES)
def test_status(client, method, url, body, expected):
    response = client.request(method, url, json=body)

    assert response.status_code == expected, response.text


def test_store_unavailable_is_503(client):
    """Error path: when the storage backend is down, every endpoint answers 503.

    Override get_store (on client.app) with a dependency that raises StoreUnavailable,
    then check one request gets 503 and the body {"detail": "storage unavailable, retry later"}.
    """
    pytest.fail("write this test")
