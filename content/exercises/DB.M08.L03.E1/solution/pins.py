"""Pinned messages (one per chat, enforced by a partial unique index) and JSON user settings.

Tables (see the tests):
  users(id, username, settings)  -- settings is NULL or a JSON object, e.g. {"notifications": false, "lang": "fa"}
  messages(id, chat_id, body, pinned)  -- pinned is 0 or 1
`conn` is in autocommit mode (isolation_level=None).
"""

import sqlite3

# A partial UNIQUE index named uq_messages_one_pin_per_chat that allows at most one pinned
# message per chat (and any number of unpinned ones). It also serves the "which message is
# pinned in chat X?" lookup.
PIN_INDEX = "CREATE UNIQUE INDEX uq_messages_one_pin_per_chat ON messages (chat_id) WHERE pinned = 1"


def pin_message(conn: sqlite3.Connection, message_id: int) -> None:
    """Make message_id the pinned message of its chat, unpinning the previous one.

    Atomic: other connections never see two pins or a half-done switch.
    LookupError if the message doesn't exist (and nothing changes).
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT chat_id FROM messages WHERE id = ?", (message_id,)).fetchone()
        if row is None:
            raise LookupError(f"no message {message_id}")
        # Unpin first: setting the new pin while the old one exists would violate the unique index.
        conn.execute("UPDATE messages SET pinned = 0 WHERE chat_id = ? AND pinned = 1 AND id != ?",
                     (row[0], message_id))
        conn.execute("UPDATE messages SET pinned = 1 WHERE id = ?", (message_id,))
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def users_with_notifications(conn: sqlite3.Connection) -> list[str]:
    """Usernames (A-Z) of users who get notifications.

    settings.notifications is a JSON boolean; when settings is NULL or has no
    "notifications" key, notifications are ON (the default). Filter in SQL.
    """
    rows = conn.execute(
        "SELECT username FROM users "
        "WHERE coalesce(settings ->> '$.notifications', 1) = 1 "
        "ORDER BY username"
    )
    return [username for (username,) in rows]
