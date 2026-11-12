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
PIN_INDEX = ""


def pin_message(conn: sqlite3.Connection, message_id: int) -> None:
    """Make message_id the pinned message of its chat, unpinning the previous one.

    Atomic: other connections never see two pins or a half-done switch.
    LookupError if the message doesn't exist (and nothing changes).
    """
    conn.execute("UPDATE messages SET pinned = 1 WHERE id = ?", (message_id,))
    chat_id = conn.execute("SELECT chat_id FROM messages WHERE id = ?", (message_id,)).fetchone()[0]
    conn.execute("UPDATE messages SET pinned = 0 WHERE chat_id = ? AND id != ?", (chat_id, message_id))


def users_with_notifications(conn: sqlite3.Connection) -> list[str]:
    """Usernames (A-Z) of users who get notifications.

    settings.notifications is a JSON boolean; when settings is NULL or has no
    "notifications" key, notifications are ON (the default). Filter in SQL.
    """
    raise NotImplementedError
