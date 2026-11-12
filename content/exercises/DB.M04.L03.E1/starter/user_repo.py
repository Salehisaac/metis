"""A repository for the users table: the only module that writes SQL for users.

Callers get User objects and domain errors, never tuples or sqlite3 exceptions.
"""

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


class UserRepository:
    def __init__(self, conn):
        self._conn = conn

    def add(self, username, now):
        """Create a user and return it. The username is stored without surrounding spaces.

        Blank username: ValueError. Username already used: UsernameTaken. The new row is committed.
        """
        raise NotImplementedError

    def get(self, user_id):
        """The User with this id, or None."""
        raise NotImplementedError

    def by_username(self, username):
        """The User with exactly this username, or None."""
        raise NotImplementedError

    def rename(self, user_id, new_username):
        """Change a user's username (stored stripped) and return the updated User.

        Blank name: ValueError. No such user: UserNotFound. Name used by someone else: UsernameTaken.
        Committed on success; nothing changes on failure.
        """
        raise NotImplementedError

    def page(self, after=None, limit=20):
        """Up to `limit` users ordered by username, starting after the username `after` (None: from the start).

        limit must be between 1 and 100, otherwise ValueError.
        """
        raise NotImplementedError
