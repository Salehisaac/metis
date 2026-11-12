```python
def join_chat(conn, chat_id, user_id):
    row = conn.execute(
        "INSERT INTO chat_members (chat_id, user_id) VALUES (?, ?) "
        "ON CONFLICT (chat_id, user_id) DO NOTHING RETURNING chat_id",
        (chat_id, user_id),
    ).fetchone()
    return row is not None


def mark_read(conn, chat_id, user_id, message_id):
    row = conn.execute(
        "INSERT INTO read_markers (chat_id, user_id, last_read_id) VALUES (?, ?, ?) "
        "ON CONFLICT (chat_id, user_id) DO UPDATE "
        "SET last_read_id = max(read_markers.last_read_id, excluded.last_read_id) "
        "RETURNING last_read_id",
        (chat_id, user_id, message_id),
    ).fetchone()
    return row[0]


def delete_chat_messages(conn, chat_id):
    rows = conn.execute("DELETE FROM messages WHERE chat_id = ? RETURNING id", (chat_id,)).fetchall()
    return sorted(row[0] for row in rows)
```

**Why it works**

- `ON CONFLICT ... DO NOTHING RETURNING ...` returns a row only when the INSERT actually happened. "Row or no
  row" is your True/False, with no SELECT first, so there's no check-then-insert gap between two concurrent joins.
- In `mark_read`, `excluded.last_read_id` is the value you tried to insert and `read_markers.last_read_id` is the
  stored one. SQLite's two-argument `max()` keeps the larger, so a late event can't move the marker backwards, and
  the UPDATE branch always runs, so `RETURNING` always returns the stored value.
  In PostgreSQL the same idea is written `GREATEST(read_markers.last_read_id, EXCLUDED.last_read_id)`.
- `DELETE ... RETURNING id` reports the deleted rows in the same statement. The docs say RETURNING rows come back
  in **arbitrary order**, so sort them yourself before promising "ascending".

**Alternative for mark_read:** `DO UPDATE SET last_read_id = excluded.last_read_id WHERE excluded.last_read_id >
read_markers.last_read_id`. That's correct too, but when the WHERE is false nothing is updated and RETURNING gives no
row, so you need a follow-up `SELECT` for the return value (allowed by the tests: the write is still one upsert).
