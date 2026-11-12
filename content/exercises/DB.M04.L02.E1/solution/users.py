"""User search and bulk import for the messenger."""

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    username: str
    created_at: str


def _user_row(cursor, row):
    return User(*row)


def _like_literal(text):
    """Escape LIKE's wildcards so they match themselves (use with ESCAPE '\\')."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def find_users(conn, text):
    """Users whose username contains `text` literally, as User objects ordered by username.

    Matching ignores ASCII case ('AN' finds 'ana'). The characters %, _ and backslash in `text`
    match only themselves. An empty `text` matches every user.
    """
    cur = conn.cursor()
    cur.row_factory = _user_row
    cur.execute(
        "SELECT id, username, created_at FROM users WHERE username LIKE ? ESCAPE '\\' ORDER BY username",
        (f"%{_like_literal(text)}%",),
    )
    return cur.fetchall()


def add_users(conn, rows):
    """Insert many users at once and return how many were inserted.

    rows is any iterable of (username, created_at) pairs, including a generator. All or nothing:
    if any row fails (e.g. a duplicate username), no row is inserted and the error reaches the caller.
    """
    with conn:
        cur = conn.executemany("INSERT INTO users (username, created_at) VALUES (?, ?)", rows)
    return cur.rowcount
