"""User search and bulk import for the messenger."""

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    username: str
    created_at: str


def find_users(conn, text):
    """Users whose username contains `text` literally, as User objects ordered by username.

    Matching ignores ASCII case ('AN' finds 'ana'). The characters %, _ and backslash in `text`
    match only themselves. An empty `text` matches every user.
    """
    raise NotImplementedError


def add_users(conn, rows):
    """Insert many users at once and return how many were inserted.

    rows is any iterable of (username, created_at) pairs, including a generator. All or nothing:
    if any row fails (e.g. a duplicate username), no row is inserted and the error reaches the caller.
    """
    raise NotImplementedError
