```python
PIN_INDEX = "CREATE UNIQUE INDEX uq_messages_one_pin_per_chat ON messages (chat_id) WHERE pinned = 1"


def pin_message(conn, message_id):
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT chat_id FROM messages WHERE id = ?", (message_id,)).fetchone()
        if row is None:
            raise LookupError(f"no message {message_id}")
        # Unpin first: setting the new pin while the old one exists would violate the unique index.
        conn.execute("UPDATE messages SET pinned = 0 WHERE chat_id = ? AND pinned = 1 AND id != ?",
                     (row[0], message_id))
        conn.execute("UPDATE messages SET pinned = 1 WHERE id = ?", (message_id,))
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def users_with_notifications(conn):
    rows = conn.execute(
        "SELECT username FROM users "
        "WHERE coalesce(settings ->> '$.notifications', 1) = 1 "
        "ORDER BY username"
    )
    return [username for (username,) in rows]
```

**Why it works**

- A **partial unique index** only contains rows matching its WHERE, so uniqueness applies only to pinned rows: one
  pinned message per chat, any number of unpinned ones. It's also tiny (one entry per chat), and the lookup
  `WHERE chat_id = ? AND pinned = 1` repeats the index's predicate, so the planner can use it.
- **Order inside the transaction matters:** the index is checked per statement, so pinning the new message before
  unpinning the old one fails with a UNIQUE error. That's what the starter did, and why it "worked" only without
  the index.
- `BEGIN IMMEDIATE` (DB.M06) makes the read and both updates one write transaction, so no other connection sees a
  chat with zero or two pins, and a missing message rolls back cleanly (`in_transaction` is False afterwards).
- `settings ->> '$.notifications'` returns SQLite's 1 or 0 for a JSON `true`/`false`, and NULL when settings is
  NULL or the key is missing. `coalesce(..., 1)` turns "missing" into the default (on). Filtering in SQL means the
  database doesn't send you every user to filter in Python.

**PostgreSQL version (not run here):** the same partial index syntax works (`WHERE pinned` with a boolean column), and
with `settings jsonb` the filter would be `coalesce((settings ->> 'notifications')::boolean, true)`, or
`NOT (settings @> '{"notifications": false}')` to use a GIN index.
