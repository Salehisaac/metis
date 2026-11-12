"""A repository for the users table: the only module that writes SQL for users.

Callers get User objects and domain errors, never tuples or sqlite3 exceptions.
"""

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    username: str
    created_at: str


class UsernameTaken(Exception):
    """Another user already has this username."""


class UserNotFound(Exception):
    """No user has this id."""


COLUMNS = "id, username, created_at"


def _clean(username):
    name = username.strip()
    if not name:
        raise ValueError("username must not be blank")
    return name


def _is_unique_violation(err):
    return getattr(err, "sqlite_errorname", "") == "SQLITE_CONSTRAINT_UNIQUE"


class UserRepository:
    def __init__(self, conn):
        self._conn = conn

    def _one(self, sql, params):
        row = self._conn.execute(sql, params).fetchone()
        return None if row is None else User(*row)

    def add(self, username, now):
        """Create a user and return it. The username is stored without surrounding spaces.

        Blank username: ValueError. Username already used: UsernameTaken. The new row is committed.
        """
        name = _clean(username)
        try:
            with self._conn:
                cur = self._conn.execute(
                    "INSERT INTO users (username, created_at) VALUES (?, ?)", (name, now)
                )
        except sqlite3.IntegrityError as err:
            if _is_unique_violation(err):
                raise UsernameTaken(name) from err
            raise
        return User(cur.lastrowid, name, now)

    def get(self, user_id):
        """The User with this id, or None."""
        return self._one(f"SELECT {COLUMNS} FROM users WHERE id = ?", (user_id,))

    def by_username(self, username):
        """The User with exactly this username, or None."""
        return self._one(f"SELECT {COLUMNS} FROM users WHERE username = ?", (username,))

    def rename(self, user_id, new_username):
        """Change a user's username (stored stripped) and return the updated User.

        Blank name: ValueError. No such user: UserNotFound. Name used by someone else: UsernameTaken.
        Committed on success; nothing changes on failure.
        """
        name = _clean(new_username)
        try:
            with self._conn:
                cur = self._conn.execute("UPDATE users SET username = ? WHERE id = ?", (name, user_id))
                if cur.rowcount == 0:
                    raise UserNotFound(user_id)
        except sqlite3.IntegrityError as err:
            if _is_unique_violation(err):
                raise UsernameTaken(name) from err
            raise
        return self.get(user_id)

    def page(self, after=None, limit=20):
        """Up to `limit` users ordered by username, starting after the username `after` (None: from the start).

        limit must be between 1 and 100, otherwise ValueError.
        """
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        rows = self._conn.execute(
            f"SELECT {COLUMNS} FROM users WHERE ? IS NULL OR username > ? ORDER BY username LIMIT ?",
            (after, after, limit),
        ).fetchall()
        return [User(*row) for row in rows]
