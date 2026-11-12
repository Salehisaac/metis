```python
SORTS = {
    "username": "username {dir}",
    "joined": "created_at {dir}, id {dir}",
}
DIRECTIONS = {"asc": "ASC", "desc": "DESC"}


def find_user(conn, username):
    sql = "SELECT id, username, created_at FROM users WHERE username = ?"
    return conn.execute(sql, (username,)).fetchone()


def recent_messages(conn, chat_id, limit):
    sql = "SELECT id, body FROM messages WHERE chat_id = ? ORDER BY sent_at DESC, id DESC LIMIT ?"
    return conn.execute(sql, (chat_id, limit)).fetchall()


def list_users(conn, sort="username", direction="asc"):
    if sort not in SORTS or direction not in DIRECTIONS:
        raise ValueError(f"unsupported sort {sort!r} {direction!r}")
    order_by = SORTS[sort].format(dir=DIRECTIONS[direction])
    return conn.execute(f"SELECT id, username FROM users ORDER BY {order_by}").fetchall()


def users_by_ids(conn, ids):
    ids = list(ids)
    if not ids:
        return []
    marks = ", ".join("?" * len(ids))
    sql = f"SELECT id, username FROM users WHERE id IN ({marks}) ORDER BY id"
    return conn.execute(sql, ids).fetchall()
```

**Why it works**

- **Placeholders keep values out of the SQL text.** The statement is compiled first, with `?` as slots; the values are bound afterwards as data. `"x' OR '1'='1"` is then just a username nobody has, and `"4 OR 1=1"` is a string that equals no integer chat_id. There's nothing to escape, because the value is never parsed as SQL.
- **Quotes are no longer special.** `o'neil` works without any escaping, for the same reason.
- **The allow-list.** A placeholder can't stand for a column or for ASC/DESC (`ORDER BY ?` would sort by a constant). So the caller's input only *selects* a key in a dict, and the SQL text comes from the dict's values, which you wrote. The f-string in `list_users` is safe because `order_by` can only be one of four fixed strings. Invalid input raises `ValueError` before the database sees anything.
- **The IN list.** `", ".join("?" * len(ids))` builds `?, ?, ?`: question marks only, never values. The f-string inserts that string, and the ids go in as parameters. The old `str(tuple(ids))` broke for one id (`(2,)` is invalid SQL) and for none (`()`), besides being injectable.

**Alternatives and limits**

- For a long id list, SQLite has a limit on the number of parameters per statement (`SQLITE_MAX_VARIABLE_NUMBER`). For thousands of ids, insert them into a temporary table and join, or use `json_each(?)` with one JSON array parameter.
- `int(chat_id)` before querying would also reject `"4 OR 1=1"` (with a ValueError), and is reasonable input validation at an API boundary. It's an extra layer, not a replacement for the placeholder.
