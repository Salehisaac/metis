"""Unread counters for chat members.

Both functions work on chat_members(chat_id, user_id, unread_count) and commit their change.
They pass the single-user tests, but they lose updates when several requests run at once.
"""

import sqlite3


def increment_unread(conn: sqlite3.Connection, chat_id: int, user_id: int) -> None:
    """Add 1 to one member's unread_count. LookupError if they aren't a member of the chat."""
    row = conn.execute(
        "SELECT unread_count FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)
    ).fetchone()
    if row is None:
        raise LookupError(f"user {user_id} is not in chat {chat_id}")
    conn.execute(
        "UPDATE chat_members SET unread_count = ? WHERE chat_id = ? AND user_id = ?",
        (row[0] + 1, chat_id, user_id),
    )
    conn.commit()


def fan_out_unread(conn: sqlite3.Connection, chat_id: int, sender_id: int) -> int:
    """A new message from sender_id: add 1 to every OTHER member's unread_count.
    Return how many members were updated (0 for an unknown chat)."""
    members = conn.execute(
        "SELECT user_id, unread_count FROM chat_members WHERE chat_id = ?", (chat_id,)
    ).fetchall()
    updated = 0
    for user_id, unread in members:
        if user_id != sender_id:
            conn.execute(
                "UPDATE chat_members SET unread_count = ? WHERE chat_id = ? AND user_id = ?",
                (unread + 1, chat_id, user_id),
            )
            updated += 1
    conn.commit()
    return updated
