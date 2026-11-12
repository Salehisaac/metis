"""Unread counters for chat members.

Both functions work on chat_members(chat_id, user_id, unread_count) and commit their change.
"""

import sqlite3


def increment_unread(conn: sqlite3.Connection, chat_id: int, user_id: int) -> None:
    """Add 1 to one member's unread_count. LookupError if they aren't a member of the chat."""
    cur = conn.execute(
        "UPDATE chat_members SET unread_count = unread_count + 1 WHERE chat_id = ? AND user_id = ?",
        (chat_id, user_id),
    )
    conn.commit()
    if cur.rowcount == 0:
        raise LookupError(f"user {user_id} is not in chat {chat_id}")


def fan_out_unread(conn: sqlite3.Connection, chat_id: int, sender_id: int) -> int:
    """A new message from sender_id: add 1 to every OTHER member's unread_count.
    Return how many members were updated (0 for an unknown chat)."""
    cur = conn.execute(
        "UPDATE chat_members SET unread_count = unread_count + 1 WHERE chat_id = ? AND user_id != ?",
        (chat_id, sender_id),
    )
    conn.commit()
    return cur.rowcount
