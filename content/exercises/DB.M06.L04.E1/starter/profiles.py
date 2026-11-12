"""Profile edits with optimistic concurrency control.

Table: users(id INTEGER PRIMARY KEY, username TEXT, bio TEXT NOT NULL, version INTEGER NOT NULL)
A client reads (bio, version), the user edits for a while, then the client saves with the version it read.
"""

import sqlite3


class ConflictError(Exception):
    """Someone else saved the profile after you read it. Re-read and try again."""


def get_profile(conn: sqlite3.Connection, user_id: int) -> tuple[str, int]:
    """Return (bio, version). LookupError if the user doesn't exist."""
    raise NotImplementedError


def update_bio(conn: sqlite3.Connection, user_id: int, new_bio: str, expected_version: int) -> int:
    """Save new_bio only if the profile is still at expected_version; return the new version.

    - ConflictError if the profile has changed since expected_version was read.
    - LookupError if the user doesn't exist.
    - Commits on success.
    """
    raise NotImplementedError
