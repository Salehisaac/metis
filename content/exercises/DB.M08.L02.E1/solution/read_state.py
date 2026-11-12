"""Membership and read markers, written with RETURNING and ON CONFLICT.

Tables (see the tests): chat_members(chat_id, user_id) PRIMARY KEY (chat_id, user_id);
read_markers(chat_id, user_id, last_read_id) PRIMARY KEY (chat_id, user_id); messages(id, chat_id, body).
`conn` is in autocommit mode (isolation_level=None): each statement commits by itself.
"""

import sqlite3


def join_chat(conn: sqlite3.Connection, chat_id: int, user_id: int) -> bool:
    """Add the membership. True if it was added, False if it already existed.
    One INSERT statement; no SELECT first (two concurrent joins must not both insert or fail)."""
    row = conn.execute(
        "INSERT INTO chat_members (chat_id, user_id) VALUES (?, ?) "
        "ON CONFLICT (chat_id, user_id) DO NOTHING RETURNING chat_id",
        (chat_id, user_id),
    ).fetchone()
    return row is not None


def mark_read(conn: sqlite3.Connection, chat_id: int, user_id: int, message_id: int) -> int:
    """Record that the user has read up to message_id in this chat, and return the stored value.

    Creates the marker if there is none. Never moves it backwards: a late, smaller message_id
    leaves the stored value as it is. The write must be a single INSERT ... ON CONFLICT statement.
    """
    row = conn.execute(
        "INSERT INTO read_markers (chat_id, user_id, last_read_id) VALUES (?, ?, ?) "
        "ON CONFLICT (chat_id, user_id) DO UPDATE "
        "SET last_read_id = max(read_markers.last_read_id, excluded.last_read_id) "
        "RETURNING last_read_id",
        (chat_id, user_id, message_id),
    ).fetchone()
    return row[0]


def delete_chat_messages(conn: sqlite3.Connection, chat_id: int) -> list[int]:
    """Delete every message of the chat in one statement and return the deleted ids, ascending."""
    rows = conn.execute("DELETE FROM messages WHERE chat_id = ? RETURNING id", (chat_id,)).fetchall()
    return sorted(row[0] for row in rows)
