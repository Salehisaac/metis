```python
EXTRA_SCHEMA = """
CREATE TABLE reactions (
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    emoji      TEXT NOT NULL CHECK (emoji <> ''),
    created_at TEXT NOT NULL,
    PRIMARY KEY (message_id, user_id, emoji)
);
CREATE TABLE blocks (
    blocker_id INTEGER NOT NULL REFERENCES users(id),
    blocked_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    PRIMARY KEY (blocker_id, blocked_id),
    CHECK (blocker_id <> blocked_id)
);
"""


def open_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(chatdb.SCHEMA + chatdb.DATA + EXTRA_SCHEMA)
    return conn
```

**Why it works**

- **The primary key is the 'only once' rule.** A reaction is identified by who, what and which emoji, so `(message_id, user_id, emoji)` is its natural key. A surrogate `id INTEGER PRIMARY KEY` would still need a `UNIQUE (message_id, user_id, emoji)`, or duplicates slip in.
- **Direction is just column order.** `(1, 2)` and `(2, 1)` are different key values, so both blocks are allowed; `(1, 2)` twice violates the primary key.
- **CHECK compares columns of the same row,** so `CHECK (blocker_id <> blocked_id)` rejects self-blocks. `CHECK (emoji <> '')` rejects the empty string; NOT NULL handles None. (A CHECK that evaluates to NULL passes, which is why NOT NULL is needed as well.)
- **ON DELETE CASCADE on reactions.message_id only.** A reaction has no meaning without its message. `user_id` keeps the default (NO ACTION), so deleting a user who has reacted fails instead of silently erasing their history; what should happen to a deleted user's data is a product decision.
- **The PRAGMA.** Without it, SQLite accepts reactions to message 999 and the CASCADE never fires. Four tests fail that way. It must run on every connection, before any transaction.

**Limits**

- The schema doesn't check that the reacting user is a **member of the message's chat**. That rule spans three tables; a foreign key can't express it unless reactions also stores chat_id with a composite foreign key to chat_members. Usually the application checks it inside the same transaction as the insert (DB.M03).
- Emoji validity isn't checked beyond "not empty". A real app would restrict it to an allowed set, in the app or with `CHECK (emoji IN (...))`.
