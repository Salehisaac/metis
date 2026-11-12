"""Two new features for the messenger: emoji reactions on messages, and blocking users.

Write the CREATE TABLE statements in EXTRA_SCHEMA, and make open_db() enforce foreign keys.

reactions(message_id, user_id, emoji, created_at)
    A user reacts to a message with an emoji. A user can put several different emoji on one message,
    but the same emoji only once. Reactions disappear with their message.
blocks(blocker_id, blocked_id, created_at)
    blocker_id has blocked blocked_id. Both are users. You can't block yourself, and blocking
    someone twice is one block. A blocks B and B blocks A are two different blocks.
"""

import sqlite3

import chatdb

EXTRA_SCHEMA = """
CREATE TABLE reactions (
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    emoji      TEXT NOT NULL CHECK (emoji <> ''),
    created_at TEXT NOT NULL,
    PRIMARY KEY (message_id, user_id, emoji)
);
CREATE TABLE blocks (
    blocker_id INTEGER NOT NULL REFERENCES users(id),
    blocked_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    PRIMARY KEY (blocker_id, blocked_id),
    CHECK (blocker_id <> blocked_id)
);
"""


def open_db():
    """A fresh in-memory messaging database: sample data plus your tables."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(chatdb.SCHEMA + chatdb.DATA + EXTRA_SCHEMA)
    return conn
