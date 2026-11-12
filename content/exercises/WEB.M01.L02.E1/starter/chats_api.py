import itertools

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI()


class ChatIn(BaseModel):
    title: str


# In-memory store: chat id -> {"id": int, "title": str}. The database arrives in WEB.M05.
chats: dict[int, dict] = {}
_ids = itertools.count(1)


# TODO: POST /chats, GET /chats/{chat_id}, PUT /chats/{chat_id}, DELETE /chats/{chat_id}
# (see exercise.json for the exact status codes, headers and bodies)
