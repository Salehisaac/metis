"""Given: the schema and a connection helper. Don't change this file."""
import sqlite3

SCHEMA = """
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    capacity INTEGER NOT NULL
);
CREATE TABLE registrations (
    event_id INTEGER NOT NULL REFERENCES events(id),
    email TEXT NOT NULL,
    UNIQUE (event_id, email)
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.executescript(SCHEMA)
    return conn
