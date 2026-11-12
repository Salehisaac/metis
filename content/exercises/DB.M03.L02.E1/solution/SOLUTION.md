```python
def create_group_chat(conn, title, creator_id, member_ids, now):
    title = title.strip()
    if not title:
        raise ValueError("title must not be blank")
    people = dict.fromkeys([creator_id, *member_ids])  # unique, first-seen order
    with conn:  # one transaction: commit if the block finishes, roll back if anything raises
        cur = conn.execute(
            "INSERT INTO chats (kind, title, created_at) VALUES ('group', ?, ?)", (title, now)
        )
        chat_id = cur.lastrowid
        for user_id in people:
            conn.execute(
                "INSERT INTO chat_members (chat_id, user_id, joined_at) VALUES (?, ?, ?)",
                (chat_id, user_id, now),
            )
        conn.execute(
            "INSERT INTO messages (chat_id, sender_id, body, sent_at) VALUES (?, ?, 'created the group', ?)",
            (chat_id, creator_id, now),
        )
    return chat_id
```

**Why it works**

- **One transaction.** In the default (legacy) mode, sqlite3 opens a transaction implicitly before the first INSERT. Nothing commits until `with conn:` ends. If the block finishes, the connection commits; if any statement raises (the unknown member's `IntegrityError`), the connection rolls back everything since the INSERT into chats, and the exception continues to the caller.
- **The rollback matters on the same connection too.** The failed INSERT is undone on its own (SQLite's default ABORT), but the chat row and earlier memberships would stay pending in an open transaction, visible to this connection, and the *next* commit, maybe from an unrelated function, would make them permanent. The test checks this with `conn.in_transaction` and counts on `conn`.
- **Duplicates are removed before the transaction.** `dict.fromkeys` keeps the first occurrence of each id, in order, so the creator is inserted first and only once. Without it, the composite primary key of chat_members rejects the second (1, 2) and the whole group creation fails.
- **Validate first.** The blank-title check needs no database, so it runs before any transaction exists.

**Alternatives**

- Explicit try/except, closer to Go's `defer tx.Rollback()` pattern:
  ```python
  try:
      ...  # the inserts
      conn.commit()
  except BaseException:
      conn.rollback()
      raise
  ```
  `with conn:` is the same thing, already written and tested for you.
- With `autocommit=False` (the Python 3.12 recommendation) the same `with conn:` code works. With `autocommit=True` it would *not*: in that mode `with conn:` does nothing, and you'd need explicit `BEGIN`/`COMMIT` statements.
- Rejecting unknown users up front with a SELECT is a nicer error message, but it doesn't replace the transaction: a user can be deleted between your SELECT and your INSERT.
