"""Group-chat use cases. Each function runs in its own transaction."""

from sqlalchemy.orm import sessionmaker

from models import Chat, ChatMember, User  # noqa: F401  (you'll need them)


def create_group(session_factory: sessionmaker, title: str, creator: str, members: list[str]) -> int:
    """Create a chat called `title` whose members are `creator` plus `members` (usernames).

    - All or nothing: if any username is unknown, raise LookupError naming the unknown
      usernames, and save nothing.
    - A blank title raises ValueError and saves nothing.
    - Duplicate usernames (or the creator repeated in members) are added once.
    Returns the new chat's id.
    """
    raise NotImplementedError


def add_member(session_factory: sessionmaker, chat_id: int, username: str) -> bool:
    """Add `username` to the chat. Return True if added, False if they were already a member.
    LookupError if the chat or the user doesn't exist."""
    raise NotImplementedError
