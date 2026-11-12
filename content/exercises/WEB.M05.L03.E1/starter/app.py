"""Messages API. Don't edit this file: the exercise is the test database in conftest.py."""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Engine, ForeignKey, String, create_engine, select
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
    title: Mapped[str] = mapped_column(String(50))


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(String(500))


class MessageIn(BaseModel):
    sender_id: int
    text: str = Field(min_length=1, max_length=500)


class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: str


def get_session(request: Request):
    with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def create_app(engine: Engine) -> FastAPI:
    app = FastAPI()
    app.state.session_factory = sessionmaker(engine, expire_on_commit=False)

    @app.post("/chats/{chat_id}/messages", status_code=201)
    def send_message(chat_id: int, body: MessageIn, session: SessionDep) -> MessageOut:
        if session.get(Chat, chat_id) is None:
            raise HTTPException(status_code=404, detail="chat not found")
        if session.get(User, body.sender_id) is None:
            raise HTTPException(status_code=404, detail="sender not found")
        message = Message(chat_id=chat_id, sender_id=body.sender_id, text=body.text)
        session.add(message)
        session.commit()
        return MessageOut(id=message.id, chat_id=chat_id, sender_id=message.sender_id, text=message.text)

    @app.get("/chats/{chat_id}/messages")
    def list_messages(chat_id: int, session: SessionDep) -> list[MessageOut]:
        if session.get(Chat, chat_id) is None:
            raise HTTPException(status_code=404, detail="chat not found")
        rows = session.scalars(select(Message).where(Message.chat_id == chat_id).order_by(Message.id))
        return [MessageOut(id=m.id, chat_id=m.chat_id, sender_id=m.sender_id, text=m.text) for m in rows]

    return app


# Production: the real database lives on the server, and tests can't (and mustn't) reach it.
production_engine = create_engine("sqlite:////var/lib/chat-api/production.db")
app = create_app(production_engine)
