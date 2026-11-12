"""The academy's messaging database: schema plus sample data. Don't edit this file.

make_db() returns a fresh in-memory connection with foreign keys enforced, so every test starts
from the same rows.
Times are UTC text 'YYYY-MM-DD HH:MM:SS', which sorts and compares correctly as text.
"""

import sqlite3

SCHEMA = """
CREATE TABLE users (
    id         INTEGER PRIMARY KEY,
    username   TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE chats (
    id         INTEGER PRIMARY KEY,
    kind       TEXT NOT NULL CHECK (kind IN ('direct', 'group')),
    title      TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE chat_members (
    chat_id   INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id   INTEGER NOT NULL REFERENCES users(id),
    joined_at TEXT NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);
CREATE TABLE messages (
    id        INTEGER PRIMARY KEY,
    chat_id   INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    sender_id INTEGER NOT NULL REFERENCES users(id),
    body      TEXT NOT NULL,
    sent_at   TEXT NOT NULL,
    edited_at TEXT
);
"""

DATA = """
INSERT INTO users (id, username, created_at) VALUES
    (1, 'ana',  '2026-10-01 10:00:00'),
    (2, 'ben',  '2026-10-03 09:00:00'),
    (3, 'chen', '2026-10-03 09:00:00'),
    (4, 'dara', '2026-11-01 08:00:00'),
    (5, 'eli',  '2026-10-20 12:00:00');
INSERT INTO chats (id, kind, title, created_at) VALUES
    (1, 'group',  'team',      '2026-10-05 09:00:00'),
    (2, 'direct', NULL,        '2026-10-06 12:00:00'),
    (3, 'group',  'book club', '2026-10-21 18:00:00'),
    (4, 'group',  'quiet',     '2026-11-01 08:30:00');
INSERT INTO chat_members (chat_id, user_id, joined_at) VALUES
    (1, 1, '2026-10-05 09:00:00'),
    (1, 2, '2026-10-05 09:00:00'),
    (1, 3, '2026-10-05 09:05:00'),
    (2, 1, '2026-10-06 12:00:00'),
    (2, 2, '2026-10-06 12:00:00'),
    (3, 2, '2026-10-21 18:00:00'),
    (3, 3, '2026-10-21 18:00:00'),
    (3, 5, '2026-10-21 18:10:00'),
    (3, 1, '2026-11-05 10:00:00'),
    (4, 4, '2026-11-01 08:30:00');
INSERT INTO messages (id, chat_id, sender_id, body, sent_at, edited_at) VALUES
    (1,  1, 1, 'morning all',        '2026-11-02 09:00:00', NULL),
    (2,  1, 2, 'hi ana',             '2026-11-02 09:01:00', NULL),
    (3,  1, 3, 'standup in 5',       '2026-11-02 09:55:00', '2026-11-02 09:56:00'),
    (4,  2, 1, 'lunch?',             '2026-11-02 12:00:00', NULL),
    (5,  2, 2, 'sure',               '2026-11-02 12:00:00', NULL),
    (6,  1, 1, 'deploy done',        '2026-11-03 17:30:00', NULL),
    (7,  1, 2, '   ',                '2026-11-03 17:31:00', NULL),
    (8,  3, 5, 'chapter 3 tonight',  '2026-11-04 20:00:00', NULL),
    (9,  3, 3, 'ok',                 '2026-11-04 20:05:00', '2026-11-04 20:06:00'),
    (10, 1, 3, 'retro notes posted', '2026-11-07 23:59:59', NULL),
    (11, 1, 1, 'thanks!',            '2026-11-08 00:00:00', NULL),
    (12, 2, 1, 'see you',            '2026-11-08 18:00:00', NULL),
    (13, 1, 2, 'friday release',     '2026-11-08 18:00:00', NULL),
    (14, 3, 2, 'joined late, hi',    '2026-11-09 08:00:00', NULL),
    (15, 1, 1, 'weekly summary',     '2026-11-09 08:00:00', '2026-11-09 08:10:00'),
    (16, 1, 3, 'release notes',      '2026-11-09 08:00:00', NULL);
"""


def make_db():
    """A fresh in-memory database with the schema and sample data."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite leaves them off unless each connection asks
    conn.executescript(SCHEMA + DATA)
    return conn


def make_file_db(path):
    """Like make_db(), but stored in a file with the sample data committed, so other connections see it."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA + DATA)
    conn.commit()
    return conn
