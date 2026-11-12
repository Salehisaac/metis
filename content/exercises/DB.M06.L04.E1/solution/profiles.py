"""Profile edits with optimistic concurrency control.

Table: users(id INTEGER PRIMARY KEY, username TEXT, bio TEXT NOT NULL, version INTEGER NOT NULL)
A client reads (bio, version), the user edits for a while, then the client saves with the version it read.
"""

import sqlite3


class ConflictError(Exception):
    """Someone else saved the profile after you read it. Re-read and try again."""


def get_profile(conn: sqlite3.Connection, user_id: int) -> tuple[str, int]:
    """Return (bio, version). LookupError if the user doesn't exist."""
    row = conn.execute("SELECT bio, version FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise LookupError(f"no user {user_id}")
    return row[0], row[1]


def update_bio(conn: sqlite3.Connection, user_id: int, new_bio: str, expected_version: int) -> int:
    """Save new_bio only if the profile is still at expected_version; return the new version.

    - ConflictError if the profile has changed since expected_version was read.
    - LookupError if the user doesn't exist.
    - Commits on success.
    """
    cur = conn.execute(
        "UPDATE users SET bio = ?, version = version + 1 WHERE id = ? AND version = ?",
        (new_bio, user_id, expected_version),
    )
    conn.commit()
    if cur.rowcount == 1:
        return expected_version + 1
    get_profile(conn, user_id)  # raises LookupError if the user is gone
    raise ConflictError(f"user {user_id} changed since version {expected_version}")
