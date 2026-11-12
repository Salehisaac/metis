"""Messenger schema with the rules enforced by the database itself.

Add the constraints listed in each table's comment, and make connect() turn on
foreign-key enforcement. Keep the table and column names.
"""

import sqlite3

SCHEMA = """
-- users: username is required and unique
CREATE TABLE users (
    id       INTEGER PRIMARY KEY,
    username TEXT
);

-- chats: kind is required and is either 'direct' or 'group';
--        a group chat must have a title (a direct chat may have none)
CREATE TABLE chats (
    id    INTEGER PRIMARY KEY,
    kind  TEXT,
    title TEXT
);

-- chat_members: chat_id and user_id are required and reference chats and users;
--               deleting a chat deletes its memberships; a user who is still a member can't be deleted;
--               role is required, defaults to 'member', and is one of 'owner', 'admin', 'member'
CREATE TABLE chat_members (
    chat_id INTEGER,
    user_id INTEGER,
    role    TEXT,
    PRIMARY KEY (chat_id, user_id)
);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """Open the database with constraints enforced and create the schema."""
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn
