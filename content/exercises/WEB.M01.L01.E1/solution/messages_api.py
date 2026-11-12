from typing import Annotated

from fastapi import FastAPI, Query

app = FastAPI()

# In-memory data; the database arrives in WEB.M05.
# Ids grow over time, so a higher id means a newer message.
MESSAGES = [
    {"id": 1, "chat_id": 10, "sender": "ali", "text": "hi", "read": True},
    {"id": 2, "chat_id": 10, "sender": "sara", "text": "hello", "read": True},
    {"id": 3, "chat_id": 20, "sender": "omid", "text": "lunch?", "read": False},
    {"id": 4, "chat_id": 10, "sender": "ali", "text": "how are you?", "read": False},
    {"id": 5, "chat_id": 10, "sender": "sara", "text": "fine", "read": False},
    {"id": 6, "chat_id": 20, "sender": "ali", "text": "yes", "read": True},
]


@app.get("/chats/{chat_id}/messages")
def list_messages(
    chat_id: int,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before: int | None = None,
    unread_only: bool = False,
):
    selected = [
        m for m in MESSAGES
        if m["chat_id"] == chat_id
        and (before is None or m["id"] < before)
        and not (unread_only and m["read"])
    ]
    newest_first = sorted(selected, key=lambda m: m["id"], reverse=True)
    return {"chat_id": chat_id, "messages": newest_first[:limit]}
