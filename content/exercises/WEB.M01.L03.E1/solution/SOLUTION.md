Five bugs, each found from the failing test's status and body:

| Test failure | Bug | Fix |
|---|---|---|
| `assert 200 == 201` on send | no `status_code` in the decorator, so success defaults to 200 | `@app.post("/messages", status_code=201)` |
| `assert 200 == 404` on a missing message; body `{"status_code": 404, ...}` | `return HTTPException(...)` sends the exception as data | `raise HTTPException(...)` |
| 422 on `/messages/pinned`, `loc` `['path', 'message_id']`, input `'pinned'` | `/messages/{message_id}` is declared first and matches `pinned` | declare `/messages/pinned` above `/messages/{message_id}` |
| 422 on edit, `loc` `['query', 'text']` | `text: str` is a single value, so FastAPI reads it from the query string | a body model `class TextEdit(BaseModel): text: str` and `body: TextEdit` |
| `KeyError: 1` raised inside the test on the second delete | `messages.pop(message_id)` crashes on a missing key | `pop(message_id, None)` and raise 404 when it returns `None` |

```python
class TextEdit(BaseModel):
    text: str


@app.post("/messages", status_code=201)
def send_message(body: NewMessage): ...


@app.get("/messages/pinned")            # fixed path first
def pinned_messages(): ...


@app.get("/messages/{message_id}")
def read_message(message_id: int):
    if message_id not in messages:
        raise HTTPException(status_code=404, detail="message not found")
    return messages[message_id]


@app.put("/messages/{message_id}/text")
def edit_message(message_id: int, body: TextEdit):
    if message_id not in messages:
        raise HTTPException(status_code=404, detail="message not found")
    messages[message_id]["text"] = body.text
    return messages[message_id]


@app.delete("/messages/{message_id}", status_code=204)
def delete_message(message_id: int):
    if messages.pop(message_id, None) is None:
        raise HTTPException(status_code=404, detail="message not found")
```

**Why it works**

- Four of the five bugs were in the **declaration** (decorator, order, parameter types), not in the logic. That's typical for FastAPI: the declaration *is* the HTTP contract.
- The `KeyError` shows up as an exception in the test, not as a 500, because `TestClient` re-raises server exceptions by default. In production the client would have seen a bare 500.
- `test_edit_without_text_is_422_from_body` checks `loc` `['body', 'text']`, so it fails if the field is still read from the query (`['query', 'text']`). Asserting on `loc` catches a bug that a status-only test would miss.

**Alternative:** a helper `get_message_or_404(message_id)` used by read, edit and delete removes the repeated check. In WEB.M03 that helper becomes a dependency.
