"""Moderation endpoints of the chat API.

Bug report: "any logged-in account can ban anyone, and can read and delete messages in
chats they're not in." Authentication works; authorization is missing. Add it.

Rules
- POST /admin/users/{user_id}/ban: moderators and admins only (others: 403).
  A moderator may ban only accounts whose role is "user"; an admin may ban anyone except
  themselves (403 otherwise). Unknown user_id: 404.
- GET /chats/{chat_id}/messages: chat members and admins. Everyone else gets 404
  "chat not found", exactly like a chat that doesn't exist.
- DELETE /chats/{chat_id}/messages/{message_id}: the message's author or an admin (204).
  Another member: 403. Someone who can't see the chat: 404 "chat not found".
"""

from dataclasses import dataclass, field
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer

from security import decode_access_token


@dataclass
class User:
    id: int
    username: str
    role: str = "user"  # "user", "moderator" or "admin"
    banned: bool = False


@dataclass
class Chat:
    id: int
    title: str
    member_ids: set[int] = field(default_factory=set)


@dataclass
class Message:
    id: int
    chat_id: int
    author_id: int
    text: str


@dataclass
class Store:
    users: dict[int, User]
    chats: dict[int, Chat]
    messages: dict[int, Message]


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def get_store(request: Request) -> Store:
    return request.app.state.store


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                     store: Annotated[Store, Depends(get_store)]) -> User:
    unauthorized = HTTPException(status_code=401, detail="Could not validate credentials",
                                 headers={"WWW-Authenticate": "Bearer"})
    try:
        user_id = int(decode_access_token(token)["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized
    user = store.users.get(user_id)
    if user is None or user.banned:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
StoreDep = Annotated[Store, Depends(get_store)]


def require_role(*roles: str):
    """Return a dependency that gives the current user if their role is in roles, else 403."""

    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user

    return dependency


def visible_chat(store: Store, chat_id: int, user: User) -> Chat:
    """The chat if user may see it. Otherwise 404, so outsiders can't tell it exists."""
    chat = store.chats.get(chat_id)
    if chat is None or (user.id not in chat.member_ids and user.role != "admin"):
        raise HTTPException(status_code=404, detail="chat not found")
    return chat


def create_app(store: Store) -> FastAPI:
    app = FastAPI()
    app.state.store = store

    @app.post("/admin/users/{user_id}/ban")
    def ban_user(user_id: int, actor: Annotated[User, Depends(require_role("moderator", "admin"))],
                 store: StoreDep) -> dict:
        target = store.users.get(user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="user not found")
        allowed = target.role == "user" if actor.role == "moderator" else target.id != actor.id
        if not allowed:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        target.banned = True
        return {"id": target.id, "banned": True}

    @app.get("/chats/{chat_id}/messages")
    def list_messages(chat_id: int, user: CurrentUser, store: StoreDep) -> list[dict]:
        visible_chat(store, chat_id, user)
        return [{"id": m.id, "author_id": m.author_id, "text": m.text}
                for m in store.messages.values() if m.chat_id == chat_id]

    @app.delete("/chats/{chat_id}/messages/{message_id}", status_code=204)
    def delete_message(chat_id: int, message_id: int, user: CurrentUser, store: StoreDep) -> None:
        visible_chat(store, chat_id, user)
        message = store.messages.get(message_id)
        if message is None or message.chat_id != chat_id:
            raise HTTPException(status_code=404, detail="message not found")
        if message.author_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Not enough permissions")
        del store.messages[message_id]

    return app
