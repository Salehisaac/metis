"""A small messages API. Don't edit this file: the exercise is about the tests."""

from datetime import datetime, timezone
from typing import Annotated, Callable

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class MessageOut(BaseModel):
    id: int
    chat_id: int
    text: str
    sent_at: datetime


class StoreUnavailable(Exception):
    """The storage backend is down."""


class Store:
    def __init__(self) -> None:
        self.chats = {1: "general", 2: "random"}  # chat_id -> title
        self.messages: list[MessageOut] = []
        self.next_id = 1


def get_store(request: Request) -> Store:
    return request.app.state.store


def get_clock() -> Callable[[], datetime]:
    return lambda: datetime.now(timezone.utc)


StoreDep = Annotated[Store, Depends(get_store)]
router = APIRouter(prefix="/chats/{chat_id}/messages")


def require_chat(store: Store, chat_id: int) -> None:
    if chat_id not in store.chats:
        raise HTTPException(status_code=404, detail="chat not found")


@router.post("", status_code=201)
def send_message(chat_id: int, body: MessageIn, store: StoreDep,
                 clock: Annotated[Callable[[], datetime], Depends(get_clock)]) -> MessageOut:
    require_chat(store, chat_id)
    message = MessageOut(id=store.next_id, chat_id=chat_id, text=body.text, sent_at=clock())
    store.next_id += 1
    store.messages.append(message)
    return message


@router.get("")
def list_messages(chat_id: int, store: StoreDep,
                  limit: Annotated[int, Query(ge=1, le=100)] = 50) -> list[MessageOut]:
    require_chat(store, chat_id)
    in_chat = [m for m in store.messages if m.chat_id == chat_id]
    return in_chat[-limit:]


@router.delete("/{message_id}", status_code=204)
def delete_message(chat_id: int, message_id: int, store: StoreDep) -> None:
    require_chat(store, chat_id)
    for m in store.messages:
        if m.chat_id == chat_id and m.id == message_id:
            store.messages.remove(m)
            return
    raise HTTPException(status_code=404, detail="message not found")


def store_unavailable(request: Request, exc: StoreUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "storage unavailable, retry later"})


def create_app() -> FastAPI:
    """A fresh app with its own empty store: chats 1 and 2 exist, no messages."""
    app = FastAPI()
    app.state.store = Store()
    app.include_router(router)
    app.add_exception_handler(StoreUnavailable, store_unavailable)
    return app
