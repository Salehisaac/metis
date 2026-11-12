"""Chat settings endpoints. Don't edit this file: the exercise is about the tests.

Rules
- Anonymous or invalid token: 401 on every endpoint.
- GET /chats/{chat_id}/members: members and admins (200). Everyone else: 404 "chat not found".
- PATCH /chats/{chat_id} {"title": ...}: the chat's owner or an admin (200). Other members: 403.
- DELETE /chats/{chat_id}/members/{user_id}: the owner or an admin may remove any member except
  the owner (204; removing the owner is 403). Other members may only remove themselves (leave).
  Someone who can't see the chat: 404.
"""

from dataclasses import dataclass, field
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from security import decode_access_token


@dataclass
class User:
    id: int
    username: str
    role: str = "user"  # "user" or "admin"


@dataclass
class Chat:
    id: int
    title: str
    owner_id: int
    member_ids: set[int] = field(default_factory=set)


@dataclass
class Store:
    users: dict[int, User]
    chats: dict[int, Chat]


class TitleIn(BaseModel):
    title: str = Field(min_length=1, max_length=50)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def get_store(request: Request) -> Store:
    return request.app.state.store


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                     store: Annotated[Store, Depends(get_store)]) -> User:
    try:
        user = store.users.get(int(decode_access_token(token)["sub"]))
    except (jwt.InvalidTokenError, ValueError):
        user = None
    if user is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
StoreDep = Annotated[Store, Depends(get_store)]


def visible_chat(store: Store, chat_id: int, user: User) -> Chat:
    chat = store.chats.get(chat_id)
    if chat is None or (user.id not in chat.member_ids and user.role != "admin"):
        raise HTTPException(status_code=404, detail="chat not found")
    return chat


def forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail="Not enough permissions")


def create_app(store: Store) -> FastAPI:
    app = FastAPI()
    app.state.store = store

    @app.get("/chats/{chat_id}/members")
    def list_members(chat_id: int, user: CurrentUser, store: StoreDep) -> list[int]:
        chat = visible_chat(store, chat_id, user)
        return sorted(chat.member_ids)

    @app.patch("/chats/{chat_id}")
    def rename_chat(chat_id: int, body: TitleIn, user: CurrentUser, store: StoreDep) -> dict:
        chat = visible_chat(store, chat_id, user)
        if user.id != chat.owner_id and user.role != "admin":
            raise forbidden()
        chat.title = body.title
        return {"id": chat.id, "title": chat.title}

    @app.delete("/chats/{chat_id}/members/{user_id}", status_code=204)
    def remove_member(chat_id: int, user_id: int, user: CurrentUser, store: StoreDep) -> None:
        chat = visible_chat(store, chat_id, user)
        if user_id not in chat.member_ids:
            raise HTTPException(status_code=404, detail="member not found")
        if user.id == chat.owner_id or user.role == "admin":
            if user_id == chat.owner_id:
                raise forbidden()
        elif user.id != user_id:
            raise forbidden()
        chat.member_ids.discard(user_id)

    return app
