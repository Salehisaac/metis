"""Read and write queries for the messenger, in SQLAlchemy 2.x style (select(), update())."""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from models import Chat, ChatMember, Message, User


def find_user(session: Session, username: str) -> User | None:
    """The User with this username, or None."""
    return session.scalars(select(User).where(User.username == username)).one_or_none()


def messages_page(session: Session, chat_id: int, before_id: int | None = None, limit: int = 20) -> list[Message]:
    """One page of a chat's history, newest first (highest id first).

    before_id=None: the newest `limit` messages. Otherwise only messages with id < before_id,
    so the client can ask for the next (older) page with the last id it received.
    """
    stmt = select(Message).where(Message.chat_id == chat_id)
    if before_id is not None:
        stmt = stmt.where(Message.id < before_id)
    return list(session.scalars(stmt.order_by(Message.id.desc()).limit(limit)))


def member_counts(session: Session) -> list[tuple[str, int]]:
    """(title, number of members) for EVERY chat, including chats with no members.
    Most members first; equal counts sorted by title A-Z."""
    member_count = func.count(ChatMember.user_id)
    stmt = (
        select(Chat.title, member_count)
        .outerjoin(ChatMember, ChatMember.chat_id == Chat.id)
        .group_by(Chat.id)
        .order_by(member_count.desc(), Chat.title)
    )
    return [(title, count) for title, count in session.execute(stmt)]


def like(session: Session, message_id: int) -> None:
    """Add 1 to a message's likes with a single UPDATE (two concurrent likes must both count).
    LookupError if the message doesn't exist. Don't commit: the caller owns the transaction."""
    result = session.execute(
        update(Message).where(Message.id == message_id).values(likes=Message.likes + 1)
    )
    if result.rowcount == 0:
        raise LookupError(f"no message {message_id}")
