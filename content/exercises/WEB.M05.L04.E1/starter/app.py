"""Send-message API. Don't edit this file: the exercise is about the tests.

Sending a message is one unit of work: the message row, the chat's message_count
and an audit entry are committed together, or not at all.
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import Engine, ForeignKey, String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(50))
    message_count: Mapped[int] = mapped_column(default=0)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    client_id: Mapped[str] = mapped_column(String(36), unique=True)  # idempotency key from the app
    text: Mapped[str] = mapped_column(String(500))


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(200))


class AuditUnavailable(Exception):
    pass


class AuditLog:
    def record(self, session: Session, action: str) -> None:
        session.add(AuditEntry(action=action))


class MessageIn(BaseModel):
    client_id: str = Field(min_length=1, max_length=36)
    text: str = Field(min_length=1, max_length=500)


def get_session(request: Request):
    with request.app.state.session_factory() as session:
        yield session


def get_audit() -> AuditLog:
    return AuditLog()


def create_app(engine: Engine) -> FastAPI:
    app = FastAPI()
    app.state.session_factory = sessionmaker(engine, expire_on_commit=False)

    @app.exception_handler(AuditUnavailable)
    def audit_unavailable(request: Request, exc: AuditUnavailable) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "audit log unavailable"})

    @app.post("/chats/{chat_id}/messages", status_code=201)
    def send_message(chat_id: int, body: MessageIn,
                     session: Annotated[Session, Depends(get_session)],
                     audit: Annotated[AuditLog, Depends(get_audit)]) -> dict:
        chat = session.get(Chat, chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="chat not found")
        try:
            message = Message(chat_id=chat_id, client_id=body.client_id, text=body.text)
            session.add(message)
            chat.message_count += 1
            audit.record(session, f"message {body.client_id} in chat {chat_id}")
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="duplicate client_id")
        return {"id": message.id, "chat_id": chat_id, "text": message.text}

    return app
