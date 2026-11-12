import itertools

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI()


class ChatIn(BaseModel):
    title: str


# In-memory store: chat id -> {"id": int, "title": str}. The database arrives in WEB.M05.
chats: dict[int, dict] = {}
_ids = itertools.count(1)


def find_chat(chat_id: int) -> dict:
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="chat not found")
    return chats[chat_id]


def ensure_title_free(title: str, except_id: int | None = None) -> None:
    for chat in chats.values():
        if chat["id"] != except_id and chat["title"].casefold() == title.casefold():
            raise HTTPException(status_code=409, detail="chat title already taken")


@app.post("/chats", status_code=status.HTTP_201_CREATED)
def create_chat(body: ChatIn, response: Response):
    ensure_title_free(body.title)
    chat = {"id": next(_ids), "title": body.title}
    chats[chat["id"]] = chat
    response.headers["Location"] = f"/chats/{chat['id']}"
    return chat


@app.get("/chats/{chat_id}")
def read_chat(chat_id: int):
    return find_chat(chat_id)


@app.put("/chats/{chat_id}")
def rename_chat(chat_id: int, body: ChatIn):
    chat = find_chat(chat_id)
    ensure_title_free(body.title, except_id=chat_id)
    chat["title"] = body.title
    return chat


@app.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: int):
    find_chat(chat_id)
    del chats[chat_id]
