"""Group-chat use cases. Each function runs in its own transaction."""

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from models import Chat, ChatMember, User


def create_group(session_factory: sessionmaker, title: str, creator: str, members: list[str]) -> int:
    """Create a chat called `title` whose members are `creator` plus `members` (usernames).

    - All or nothing: if any username is unknown, raise LookupError naming the unknown
      usernames, and save nothing.
    - A blank title raises ValueError and saves nothing.
    - Duplicate usernames (or the creator repeated in members) are added once.
    Returns the new chat's id.
    """
    if not title.strip():
        raise ValueError("title must not be blank")
    wanted = list(dict.fromkeys([creator, *members]))  # unique, order kept
    with session_factory.begin() as session:
        found = session.scalars(select(User).where(User.username.in_(wanted))).all()
        by_name = {u.username: u for u in found}
        missing = [name for name in wanted if name not in by_name]
        if missing:
            raise LookupError(f"unknown users: {', '.join(missing)}")
        chat = Chat(title=title)
        session.add(chat)
        session.flush()  # INSERT now, so chat.id is known
        session.add_all([ChatMember(chat_id=chat.id, user_id=by_name[name].id) for name in wanted])
        return chat.id


def add_member(session_factory: sessionmaker, chat_id: int, username: str) -> bool:
    """Add `username` to the chat. Return True if added, False if they were already a member.
    LookupError if the chat or the user doesn't exist."""
    with session_factory.begin() as session:
        if session.get(Chat, chat_id) is None:
            raise LookupError(f"no chat {chat_id}")
        user = session.scalars(select(User).where(User.username == username)).one_or_none()
        if user is None:
            raise LookupError(f"no user {username}")
        if session.get(ChatMember, (chat_id, user.id)) is not None:
            return False
        session.add(ChatMember(chat_id=chat_id, user_id=user.id))
        return True
