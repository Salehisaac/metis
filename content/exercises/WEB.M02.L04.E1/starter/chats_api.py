# Don't edit this file: the app is finished. Your work is in errors.py.
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from errors import AppError, install_error_handlers

app = FastAPI()
install_error_handlers(app)


class ChatIn(BaseModel):
    title: str = Field(min_length=1, max_length=64)

    @field_validator("title")
    @classmethod
    def no_mention_prefix(cls, value: str) -> str:
        if value.startswith("@"):
            raise ValueError("title must not start with @")
        return value


chats = {1: {"id": 1, "title": "Family"}}


@app.get("/chats/{chat_id}")
def read_chat(chat_id: int):
    if chat_id not in chats:
        raise AppError(404, "chat_not_found", f"chat {chat_id} not found")
    return chats[chat_id]


@app.post("/chats", status_code=201)
def create_chat(body: ChatIn):
    if any(c["title"] == body.title for c in chats.values()):
        raise HTTPException(status_code=409, detail="chat title already taken")
    chat = {"id": max(chats) + 1, "title": body.title}
    chats[chat["id"]] = chat
    return chat


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int):
    raise HTTPException(status_code=401, detail="login required", headers={"WWW-Authenticate": "Bearer"})


@app.get("/teapot")
def teapot():
    raise HTTPException(status_code=418, detail="I'm a teapot")
