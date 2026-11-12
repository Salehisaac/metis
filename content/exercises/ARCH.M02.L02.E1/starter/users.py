"""User reads go through a Redis cache; email changes must invalidate it correctly.

get_user is correct. update_email has three bugs: find and fix them.
"""
import json
import logging
import sqlite3

import redis  # noqa: F401  (redis.RedisError is the base class of its errors)

log = logging.getLogger("users")
USER_TTL = 300


class UserNotFound(Exception):
    pass


def user_key(user_id: int) -> str:
    return f"cache:user:{user_id}"


def get_user(conn: sqlite3.Connection, r, user_id: int) -> dict | None:
    key = user_key(user_id)
    cached = r.get(key)
    if cached is not None:
        return json.loads(cached)
    row = conn.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    user = {"id": row[0], "email": row[1]}
    r.set(key, json.dumps(user), ex=USER_TTL)
    return user


def update_email(conn: sqlite3.Connection, r, user_id: int, email: str) -> None:
    """Change the user's email, then make sure readers stop seeing the old one.

    - The database is the source of truth: once the UPDATE is committed, the change counts as done.
    - Raise UserNotFound if there is no such user.
    """
    email = email.strip().lower()
    try:
        r.delete(f"user:{user_id}")
    except Exception:
        pass
    with conn:
        cur = conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
    if cur.rowcount == 0:
        raise UserNotFound(user_id)

