"""Four lookup functions from the messenger's admin tool. All four build SQL with f-strings.

Every one of them can be attacked with SQL injection, and two of them also crash on harmless input.
Rewrite them so no caller-supplied value is ever pasted into SQL text.
"""


def find_user(conn, username):
    """(id, username, created_at) of the user with exactly this username, or None."""
    sql = f"SELECT id, username, created_at FROM users WHERE username = '{username}'"
    return conn.execute(sql).fetchone()


def recent_messages(conn, chat_id, limit):
    """(id, body) of the chat's `limit` newest messages, newest first (sent_at, then id)."""
    sql = f"SELECT id, body FROM messages WHERE chat_id = {chat_id} ORDER BY sent_at DESC, id DESC LIMIT {limit}"
    return conn.execute(sql).fetchall()


def list_users(conn, sort="username", direction="asc"):
    """(id, username) of every user.

    sort: 'username', or 'joined' (by created_at, ties by id). direction: 'asc' or 'desc' (applies to
    every sort key). Any other sort or direction raises ValueError.
    """
    sql = f"SELECT id, username FROM users ORDER BY {sort} {direction}"
    return conn.execute(sql).fetchall()


def users_by_ids(conn, ids):
    """(id, username) of the users whose id is in `ids`, ordered by id. Unknown ids are skipped; no ids: []."""
    sql = f"SELECT id, username FROM users WHERE id IN {tuple(ids)} ORDER BY id"
    return conn.execute(sql).fetchall()
