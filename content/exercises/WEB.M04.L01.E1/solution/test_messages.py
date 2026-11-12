"""Reference tests for the messages endpoints."""


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
