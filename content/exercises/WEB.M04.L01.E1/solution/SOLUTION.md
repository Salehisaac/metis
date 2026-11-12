```python
def test_send_message_returns_201_and_the_message(client):
    payload = {"text": "deploy at 5?"}

    response = client.post("/chats/2/messages", json=payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] == 1
    assert body["chat_id"] == 2
    assert body["text"] == "deploy at 5?"
    assert "sent_at" in body


def test_send_to_unknown_chat_is_404(client):
    response = client.post("/chats/999/messages", json={"text": "anyone?"})

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "chat not found"


def test_blank_text_is_422(client):
    response = client.post("/chats/1/messages", json={"text": "   "})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "text"]


def test_list_shows_only_this_chat(client):
    client.post("/chats/1/messages", json={"text": "only in general"})

    response = client.get("/chats/2/messages")

    assert response.status_code == 200
    assert response.json() == []


def test_list_keeps_sending_order(client):
    client.post("/chats/1/messages", json={"text": "first"})
    client.post("/chats/1/messages", json={"text": "second"})

    response = client.get("/chats/1/messages")

    assert response.status_code == 200
    assert [m["text"] for m in response.json()] == ["first", "second"]
```

**Which test kills which mutant**

| Mutant | Killed by |
|---|---|
| `created_is_200` | `test_send_message_returns_201_and_the_message` (asserts 201, not just "2xx") |
| `unknown_chat_accepted` | `test_send_to_unknown_chat_is_404` |
| `blank_accepted` | `test_blank_text_is_422` (`"   "` has length 3, so `min_length=1` alone doesn't reject it) |
| `wrong_chat_id` | `test_send_message_returns_201_and_the_message`, **only** because it posts to chat 2 and asserts `chat_id == 2` |
| `other_chats_listed` | `test_list_shows_only_this_chat`: the Arrange step puts a message in chat 1, then lists chat 2 |
| `newest_first` | `test_list_keeps_sending_order` (one message can't reveal an order bug) |

**Why it works**

- **Assert what the spec fixes, skip what it doesn't.** `id` is 1 in a fresh app and `chat_id`/`text` echo the input, so they are asserted exactly. `sent_at` is "now", so the test only checks that it's there. Freezing the clock with `dependency_overrides` (next lesson) would let you assert it exactly.
- **The Arrange step creates the situation the bug needs.** "Lists other chats" is invisible when only one chat has messages, and "wrong order" is invisible with one message. Edge-case tests are mostly about choosing the Arrange data.
- **422 tests assert on `loc`, not on `msg`.** The message text belongs to Pydantic and can change between versions; the location of the error (`["body", "text"]`) is your API contract.

**Alternative:** you could compare the whole body with `==` after removing the unpredictable field: `body.pop("sent_at")`, then `assert body == {"id": 1, "chat_id": 2, "text": "deploy at 5?"}`. That also catches unexpected *extra* fields.
