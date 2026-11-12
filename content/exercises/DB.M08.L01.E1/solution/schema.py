"""Messenger schema with the rules enforced by the database itself."""

import sqlite3

SCHEMA = """
CREATE TABLE users (
    id       INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE
);

CREATE TABLE chats (
    id    INTEGER PRIMARY KEY,
    kind  TEXT NOT NULL CONSTRAINT chk_chats_kind CHECK (kind IN ('direct', 'group')),
    title TEXT,
    CONSTRAINT chk_chats_group_has_title CHECK (kind = 'direct' OR title IS NOT NULL)
);

CREATE TABLE chat_members (
    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    role    TEXT NOT NULL DEFAULT 'member'
            CONSTRAINT chk_chat_members_role CHECK (role IN ('owner', 'admin', 'member')),
    PRIMARY KEY (chat_id, user_id)
);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """Open the database with constraints enforced and create the schema."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
