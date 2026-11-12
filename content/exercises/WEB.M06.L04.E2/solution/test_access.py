"""Reference access-control table for app.py."""

import pytest

from conftest import ALI, BAD_TOKEN, EVE, OLGA, ROOT

NEW_TITLE = {"title": "renamed"}

CASES = [
    pytest.param(ALI, "GET", "/chats/1/members", None, 200, id="member-lists-members"),
    pytest.param(None, "GET", "/chats/1/members", None, 401, id="anonymous-lists-members"),
    pytest.param(BAD_TOKEN, "GET", "/chats/1/members", None, 401, id="bad-token-lists-members"),
    pytest.param(ROOT, "GET", "/chats/1/members", None, 200, id="admin-lists-members"),
    pytest.param(EVE, "GET", "/chats/1/members", None, 404, id="outsider-lists-members"),
    # rename
    pytest.param(OLGA, "PATCH", "/chats/1", NEW_TITLE, 200, id="owner-renames"),
    pytest.param(ROOT, "PATCH", "/chats/1", NEW_TITLE, 200, id="admin-renames"),
    pytest.param(ALI, "PATCH", "/chats/1", NEW_TITLE, 403, id="member-renames"),
    pytest.param(EVE, "PATCH", "/chats/1", NEW_TITLE, 404, id="outsider-renames"),
    pytest.param(None, "PATCH", "/chats/1", NEW_TITLE, 401, id="anonymous-renames"),
    # remove member
    pytest.param(OLGA, "DELETE", "/chats/1/members/2", None, 204, id="owner-removes-member"),
    pytest.param(ROOT, "DELETE", "/chats/1/members/2", None, 204, id="admin-removes-member"),
    pytest.param(ALI, "DELETE", "/chats/1/members/2", None, 204, id="member-leaves"),
    pytest.param(ALI, "DELETE", "/chats/1/members/3", None, 403, id="member-removes-other"),
    pytest.param(ROOT, "DELETE", "/chats/1/members/1", None, 403, id="admin-removes-owner"),
    pytest.param(EVE, "DELETE", "/chats/1/members/2", None, 404, id="outsider-removes-member"),
    pytest.param(None, "DELETE", "/chats/1/members/2", None, 401, id="anonymous-removes-member"),
]


@pytest.mark.parametrize("actor, method, url, body, expected", CASES)
def test_access(client, actor, method, url, body, expected):
    from conftest import headers

    response = client.request(method, url, json=body, headers=headers(actor))

    assert response.status_code == expected, response.text


def test_every_endpoint_has_401_403_and_404_rows():
    """Your table must contain, for each of the three endpoints, at least one 401, one 403
    (members list: not applicable) and one 404 row."""
    by_endpoint = {}
    for case in CASES:
        actor, method, url, body, expected = case.values
        endpoint = "members" if method == "GET" else ("rename" if method == "PATCH" else "remove")
        by_endpoint.setdefault(endpoint, set()).add(expected)
    assert {401, 404} <= by_endpoint.get("members", set())
    assert {401, 403, 404} <= by_endpoint.get("rename", set())
    assert {401, 403, 404} <= by_endpoint.get("remove", set())
