"""ORM models for the messenger. User and Message are done; map Contact and Reaction."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str]


# TODO: class Contact(Base) -> table "contacts"
#   owner_id    -> users.id, part of the primary key
#   contact_id  -> users.id, part of the primary key
#   nickname    optional text, at most 64 characters
#   added_at    required datetime, filled in by the database (CURRENT_TIMESTAMP)


# TODO: class Reaction(Base) -> table "reactions"
#   id          integer primary key
#   message_id  -> messages.id, required
#   user_id     -> users.id, required
#   emoji       required text, at most 16 characters
#   a user can add the same emoji to the same message only once
#     (a UniqueConstraint on message_id, user_id, emoji named "uq_reactions_message_user_emoji")
