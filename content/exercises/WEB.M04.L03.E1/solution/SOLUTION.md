```python
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


def test_store_unavailable_is_503(client):
    def store_down():
        raise StoreUnavailable()

    client.app.dependency_overrides[get_store] = store_down

    response = client.get("/chats/1/messages")

    assert response.status_code == 503
    assert response.json() == {"detail": "storage unavailable, retry later"}
```

**Which rows kill which mutant**

| Mutant | Killed by |
|---|---|
| `limit_zero_allowed` | `list-limit-0` |
| `limit_max_too_high` | `list-limit-101` |
| `text_too_long_allowed` | `send-501-chars` |
| `delete_returns_200` | `delete-ok` |
| `delete_ignores_chat` | `delete-message-of-other-chat` |
| `list_unknown_chat_200` | `list-unknown-chat` |
| `no_503_handler` | `test_store_unavailable_is_503`: without the handler the exception escapes, and TestClient re-raises it in the test |

**Why it works**

- **Both sides of every boundary.** `limit-1` and `limit-100` prove the valid edges still work; `limit-0` and `limit-101` prove the invalid ones are rejected. An off-by-one bug moves exactly one of these.
- **The seeded data creates the edge cases.** "A message id that exists, but in another chat" can only be tested because chat 1 has message 1. In production that row is an authorization bug: deleting someone else's message by guessing its id (you'll meet this again in WEB.M06).
- **The error path needs a fake.** You can't make the real store go down on demand, but `dependency_overrides` can swap in a function that raises. The test then checks the exception handler turns it into a clean 503 instead of a crash.

**Alternative:** split the table into one parametrized test per endpoint (`SEND_CASES`, `LIST_CASES`, ...). That reads better once a table has more than about 15 rows.
