import itertools

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class NewMessage(BaseModel):
    chat_id: int
    text: str


class TextEdit(BaseModel):
    text: str


messages: dict[int, dict] = {
    1: {"id": 1, "chat_id": 10, "text": "hi", "pinned": False},
    2: {"id": 2, "chat_id": 10, "text": "standup at 10", "pinned": True},
}
_ids = itertools.count(3)


@app.post("/messages", status_code=201)
def send_message(body: NewMessage):
    message = {"id": next(_ids), "chat_id": body.chat_id, "text": body.text, "pinned": False}
    messages[message["id"]] = message
    return message


@app.get("/messages/pinned")
def pinned_messages():
    return [m for m in messages.values() if m["pinned"]]


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
