```python
def _user_row(cursor, row):
    return User(*row)


def _like_literal(text):
    """Escape LIKE's wildcards so they match themselves (use with ESCAPE '\\')."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def find_users(conn, text):
    cur = conn.cursor()
    cur.row_factory = _user_row
    cur.execute(
        "SELECT id, username, created_at FROM users WHERE username LIKE ? ESCAPE '\\' ORDER BY username",
        (f"%{_like_literal(text)}%",),
    )
    return cur.fetchall()


def add_users(conn, rows):
    with conn:
        cur = conn.executemany("INSERT INTO users (username, created_at) VALUES (?, ?)", rows)
    return cur.rowcount
```

**Why it works**

- **Two different escapings, two different jobs.** The placeholder keeps the text out of the SQL statement: no injection, quotes like `o'n` need nothing. But LIKE then interprets the *value* as a pattern, where `%` means "anything" and `_` means "any one character". `ESCAPE '\'` declares backslash as the pattern's escape character, so `\%`, `\_` and `\\` match a literal `%`, `_` and `\`. This is pattern escaping inside a bound value, which is legitimate; it's not the SQL-text escaping that DB.M04.L01 warned about.
- **Backslash first.** If you replaced `%` first, the backslashes you just added would then be doubled by the backslash step, and `%` would no longer be escaped.
- **Case.** SQLite's LIKE ignores case for ASCII letters only, so 'AN' finds 'ana' (but 'Ä' wouldn't find 'ä').
- **Row factory on a cursor.** Setting `row_factory` on a cursor affects only that cursor, so the connection keeps returning tuples elsewhere. `User(*row)` relies on the SELECT listing columns in the dataclass's field order.
- **executemany in `with conn:`.** One statement, run once per row; the duplicate 'ana' raises `IntegrityError`, the block rolls back 'hal' too, and the error propagates. `executemany` accepts any iterable, so a generator streams rows without building a list. `rowcount` after executemany is the total number of rows inserted.

**Alternatives**

- `instr(lower(username), lower(?)) > 0` finds a literal substring with no wildcards to escape at all. It reads less familiar; and for searching message text at scale, full-text search (SQLite's FTS5 extension) is the better tool. DB.M05 looks at what such queries cost.
- A connection-wide `conn.row_factory = sqlite3.Row` gives name-based access (`row["username"]`) without a dataclass, which is often enough for internal code.
