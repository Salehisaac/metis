"""Four lookup functions from the messenger's admin tool. All four build SQL with f-strings.

Every one of them can be attacked with SQL injection, and two of them also crash on harmless input.
Rewrite them so no caller-supplied value is ever pasted into SQL text.
"""

# Identifiers and keywords can't be placeholders: map each allowed choice to fixed SQL text.
SORTS = {
    "username": "username {dir}",
    "joined": "created_at {dir}, id {dir}",
}
DIRECTIONS = {"asc": "ASC", "desc": "DESC"}


def find_user(conn, username):
    """(id, username, created_at) of the user with exactly this username, or None."""
    sql = "SELECT id, username, created_at FROM users WHERE username = ?"
    return conn.execute(sql, (username,)).fetchone()


def recent_messages(conn, chat_id, limit):
    """(id, body) of the chat's `limit` newest messages, newest first (sent_at, then id)."""
    sql = "SELECT id, body FROM messages WHERE chat_id = ? ORDER BY sent_at DESC, id DESC LIMIT ?"
    return conn.execute(sql, (chat_id, limit)).fetchall()


def list_users(conn, sort="username", direction="asc"):
    """(id, username) of every user.

    sort: 'username', or 'joined' (by created_at, ties by id). direction: 'asc' or 'desc' (applies to
    every sort key). Any other sort or direction raises ValueError.
    """
    if sort not in SORTS or direction not in DIRECTIONS:
        raise ValueError(f"unsupported sort {sort!r} {direction!r}")
    order_by = SORTS[sort].format(dir=DIRECTIONS[direction])  # only fixed, allow-listed text
    return conn.execute(f"SELECT id, username FROM users ORDER BY {order_by}").fetchall()


def users_by_ids(conn, ids):
    """(id, username) of the users whose id is in `ids`, ordered by id. Unknown ids are skipped; no ids: []."""
    ids = list(ids)
    if not ids:
        return []
    marks = ", ".join("?" * len(ids))  # one placeholder per value; the values stay separate
    sql = f"SELECT id, username FROM users WHERE id IN ({marks}) ORDER BY id"
    return conn.execute(sql, ids).fetchall()
