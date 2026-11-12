```python
def increment_unread(conn, chat_id, user_id):
    cur = conn.execute(
        "UPDATE chat_members SET unread_count = unread_count + 1 WHERE chat_id = ? AND user_id = ?",
        (chat_id, user_id),
    )
    conn.commit()
    if cur.rowcount == 0:
        raise LookupError(f"user {user_id} is not in chat {chat_id}")


def fan_out_unread(conn, chat_id, sender_id):
    cur = conn.execute(
        "UPDATE chat_members SET unread_count = unread_count + 1 WHERE chat_id = ? AND user_id != ?",
        (chat_id, sender_id),
    )
    conn.commit()
    return cur.rowcount
```

**The bug:** both starter functions read `unread_count` into Python, add 1, and write the number back. The read and
the write are separate statements (separate transactions), so two requests can both read 5 and both write 6.

**Why the fix works**

- `SET unread_count = unread_count + 1` makes the database compute the new value from the **current** value while it
  holds the write lock for that statement. There's no gap between read and write for another writer to slip into.
- One statement is also one round trip, and `fan_out_unread` does all members in a single UPDATE instead of a loop.
- `cursor.rowcount` tells you how many rows the UPDATE changed. 0 means "no such member", which replaces the old
  SELECT that only existed to check membership. Nothing was changed in that case, so committing first is harmless.
- `user_id != ?` excludes the sender in SQL, so the count returned is exactly the number of rows updated.

**Alternative:** when the new value needs real Python logic between read and write (not just `+ 1`), keep the
SELECT but put both statements in one `BEGIN IMMEDIATE` transaction (your `write_transaction()` from L02). That
takes the write lock before reading, so nobody can change the row in between. Prefer the single UPDATE when it can
express the change: it holds the lock for less time.
