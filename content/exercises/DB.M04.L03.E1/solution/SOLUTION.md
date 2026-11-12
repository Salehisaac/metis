```python
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
        return self._one(f"SELECT {COLUMNS} FROM users WHERE id = ?", (user_id,))

    def by_username(self, username):
        return self._one(f"SELECT {COLUMNS} FROM users WHERE username = ?", (username,))

    def rename(self, user_id, new_username):
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
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        rows = self._conn.execute(
            f"SELECT {COLUMNS} FROM users WHERE ? IS NULL OR username > ? ORDER BY username LIMIT ?",
            (after, after, limit),
        ).fetchall()
        return [User(*row) for row in rows]
```

**Why it works**

- **Validate first, then one transaction.** `_clean` runs before any SQL, so a blank name never opens a transaction. Each write is one `with self._conn:` block: committed when it finishes, rolled back when anything inside raises, including our own `UserNotFound`.
- **Translate narrowly.** Only a UNIQUE violation becomes `UsernameTaken`; `sqlite_errorname` (Python 3.11+) distinguishes it from NOT NULL or CHECK failures, which are bugs and are re-raised unchanged. `raise ... from err` keeps the IntegrityError as `__cause__`, like `%w` in Go.
- **The catch is outside the `with`.** The block has already rolled back by the time the except runs, so the connection is clean (`in_transaction` is False) when the caller sees `UsernameTaken`.
- **`rowcount == 0` means unknown id.** An UPDATE matching nothing is not an error (DB.M01.L02), so the repository turns it into `UserNotFound` itself.
- **Keyset paging.** `username > ?` continues exactly after the last name the caller saw. Unlike OFFSET, it doesn't skip or repeat rows when users are added between page requests, and it doesn't re-read the skipped rows. `? IS NULL OR ...` handles the first page with one SQL string.
- **The f-strings are safe** because `COLUMNS` is a constant in this module, not input.

**Alternatives and limits**

- Checking `by_username` before inserting gives a friendlier code path but is racy: two requests can both see "free" and then one hits the UNIQUE constraint anyway. Keep the constraint and the translation either way.
- A `sqlite3.Row` or custom `row_factory` would replace `User(*row)`; `User(*row)` is fine while the SELECT always lists `COLUMNS` in field order.
- This repository commits per method. When one use case must change several tables atomically (say, create a user and their first chat), the transaction belongs one level up, in a service that calls repositories that don't commit themselves. Deciding that boundary is part of PRJ-02.
