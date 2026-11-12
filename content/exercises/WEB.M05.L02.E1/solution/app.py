"""Chats API: creating a chat, its members and an optional first message is one unit of work."""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Engine, ForeignKey, String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(50), unique=True)


class Member(Base):
    __tablename__ = "members"

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(String(500))


class ChatIn(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    member_ids: list[int] = Field(min_length=1)
    first_message: str | None = Field(default=None, min_length=1, max_length=500)


class ChatOut(BaseModel):
    id: int
    title: str
    member_ids: list[int]


def get_session(request: Request):
    with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def create_app(engine: Engine) -> FastAPI:
    app = FastAPI()
    app.state.session_factory = sessionmaker(engine)

    @app.post("/chats", status_code=201)
    def create_chat(body: ChatIn, session: SessionDep) -> ChatOut:
        try:
            chat = Chat(title=body.title)
            session.add(chat)
            session.flush()  # sends the INSERT, so chat.id is known; nothing is committed yet

            for user_id in body.member_ids:
                if session.get(User, user_id) is None:
                    raise HTTPException(status_code=404, detail=f"user {user_id} not found")
                session.add(Member(chat_id=chat.id, user_id=user_id))

            if body.first_message is not None:
                session.add(Message(chat_id=chat.id, sender_id=body.member_ids[0], text=body.first_message))

            session.commit()  # the only commit: all three writes, or none
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="chat title taken or duplicate member")

        return ChatOut(id=chat.id, title=chat.title, member_ids=body.member_ids)

    return app
