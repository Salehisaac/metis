from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

USERS = {1: {"id": 1, "username": "ali"}, 2: {"id": 2, "username": "sara"}, 3: {"id": 3, "username": "omid"}}
CHATS = {10: {"id": 10, "title": "Backend team", "members": {1, 2}}}
MESSAGES: list[dict] = []
tx_log: list[str] = []


class Transaction:
    """Stand-in for a database transaction (WEB.M05): messages stay pending until commit()."""

    def __init__(self):
        self.pending: list[dict] = []
        tx_log.append("begin")

    def add_message(self, message: dict) -> None:
        self.pending.append(message)

    def commit(self) -> None:
        MESSAGES.extend(self.pending)
        self.pending.clear()
        tx_log.append("commit")

    def rollback(self) -> None:
        self.pending.clear()
        tx_log.append("rollback")

    def close(self) -> None:
        tx_log.append("close")


def get_tx():
    """Yield one Transaction per request. Roll back on any exception and re-raise it. Always close."""
    db = Transaction()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(x_user_id: Annotated[int | None, Header()] = None) -> dict:
    """The user named by the X-User-Id header, or 401."""
    user = USERS.get(x_user_id) if x_user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="missing or unknown X-User-Id")
    return user


def get_member_chat(chat_id: int, user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """The chat from the path, if the current user is a member: 404 for no such chat, 403 for non-members."""
    chat = CHATS.get(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="chat not found")
    if user["id"] not in chat["members"]:
        raise HTTPException(status_code=403, detail="not a member of this chat")
    return chat


# ---- The routes are finished. ----

Tx = Annotated[Transaction, Depends(get_tx)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
MemberChat = Annotated[dict, Depends(get_member_chat)]

app = FastAPI()


class NewMessage(BaseModel):
    text: str


class Batch(BaseModel):
    texts: list[str]


@app.post("/chats/{chat_id}/messages", status_code=201)
def send_message(chat: MemberChat, user: CurrentUser, tx: Tx, body: NewMessage):
    message = {"chat_id": chat["id"], "sender_id": user["id"], "text": body.text}
    tx.add_message(message)
    tx.commit()
    return message


@app.post("/chats/{chat_id}/messages/batch", status_code=201)
def send_batch(chat: MemberChat, user: CurrentUser, tx: Tx, body: Batch):
    for text in body.texts:
        if not text.strip():
            raise HTTPException(status_code=422, detail="empty message in batch")
        tx.add_message({"chat_id": chat["id"], "sender_id": user["id"], "text": text})
    tx.commit()
    return {"sent": len(body.texts)}


@app.get("/chats/{chat_id}/messages")
def history(chat: MemberChat):
    return [m for m in MESSAGES if m["chat_id"] == chat["id"]]


@app.post("/debug/crash")
def crash(tx: Tx):
    tx.add_message({"chat_id": 10, "sender_id": 1, "text": "never stored"})
    raise RuntimeError("simulated bug")
