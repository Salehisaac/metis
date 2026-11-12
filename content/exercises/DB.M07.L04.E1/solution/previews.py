"""Read models for the chat list screen, without N+1 queries."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from models import Chat, Message


def chat_member_lists(session: Session) -> list[tuple[str, list[str]]]:
    """(title, member usernames sorted A-Z) for every chat, ordered by title."""
    stmt = select(Chat).options(selectinload(Chat.members)).order_by(Chat.title)
    result = []
    for chat in session.scalars(stmt):
        result.append((chat.title, sorted(user.username for user in chat.members)))
    return result


def latest_with_senders(session: Session, chat_id: int, limit: int = 10) -> list[tuple[str, str]]:
    """(sender username, body) for the chat's newest `limit` messages, newest first."""
    stmt = (
        select(Message)
        .options(joinedload(Message.sender))
        .where(Message.chat_id == chat_id)
        .order_by(Message.id.desc())
        .limit(limit)
    )
    return [(message.sender.username, message.body) for message in session.scalars(stmt)]
