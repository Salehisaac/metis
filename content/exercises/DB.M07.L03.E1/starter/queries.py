"""Read and write queries for the messenger, in SQLAlchemy 2.x style (select(), update())."""

from sqlalchemy.orm import Session

from models import Chat, ChatMember, Message, User  # noqa: F401  (you'll need them)


def find_user(session: Session, username: str) -> User | None:
    """The User with this username, or None."""
    raise NotImplementedError


def messages_page(session: Session, chat_id: int, before_id: int | None = None, limit: int = 20) -> list[Message]:
    """One page of a chat's history, newest first (highest id first).

    before_id=None: the newest `limit` messages. Otherwise only messages with id < before_id,
    so the client can ask for the next (older) page with the last id it received.
    """
    raise NotImplementedError


def member_counts(session: Session) -> list[tuple[str, int]]:
    """(title, number of members) for EVERY chat, including chats with no members.
    Most members first; equal counts sorted by title A-Z."""
    raise NotImplementedError


def like(session: Session, message_id: int) -> None:
    """Add 1 to a message's likes with a single UPDATE (two concurrent likes must both count).
    LookupError if the message doesn't exist. Don't commit: the caller owns the transaction."""
    raise NotImplementedError
