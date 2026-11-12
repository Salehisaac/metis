"""Read models for the chat list screen. The results are right, but the query count isn't."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Chat, Message


def chat_member_lists(session: Session) -> list[tuple[str, list[str]]]:
    """(title, member usernames sorted A-Z) for every chat, ordered by title."""
    result = []
    for chat in session.scalars(select(Chat).order_by(Chat.title)):
        result.append((chat.title, sorted(user.username for user in chat.members)))
    return result


def latest_with_senders(session: Session, chat_id: int, limit: int = 10) -> list[tuple[str, str]]:
    """(sender username, body) for the chat's newest `limit` messages, newest first."""
    stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.id.desc()).limit(limit)
    return [(message.sender.username, message.body) for message in session.scalars(stmt)]
