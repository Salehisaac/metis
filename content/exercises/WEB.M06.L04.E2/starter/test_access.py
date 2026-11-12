"""YOUR access-control table for app.py.

Grow CASES: one row per request, (actor, method, url, json_body_or_None, expected_status).
actor is a user id from conftest.py, None (no token) or BAD_TOKEN. Every row runs on a fresh app.
Keep the two rows that are here: the exercise looks for their test ids.
Cover 401, 403 and 404 for every endpoint, and the allowed cases too.
test_meta.py runs your rows against seven broken copies of app.py; each must make a row fail.
"""

import pytest

from conftest import ALI, BAD_TOKEN, EVE, OLGA, ROOT, SARA  # noqa: F401  (use them in your rows)

CASES = [
    pytest.param(ALI, "GET", "/chats/1/members", None, 200, id="member-lists-members"),
    pytest.param(None, "GET", "/chats/1/members", None, 401, id="anonymous-lists-members"),
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
