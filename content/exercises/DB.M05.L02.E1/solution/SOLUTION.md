```python
INDEXES: list[str] = [
    "CREATE INDEX idx_chat_members_user_joined_chat ON chat_members (user_id, joined_at, chat_id)",
    "CREATE INDEX idx_messages_chat_created ON messages (chat_id, created_at)",
    "CREATE INDEX idx_messages_sender_chat ON messages (sender_id, chat_id)",
]
```

**Why each index looks like this**

| Query | Index | Why |
|---|---|---|
| MY_CHATS | `(user_id, joined_at, chat_id)` | The primary key starts with `chat_id`, so it can't find a user's rows. Equality column first (`user_id`), then the ORDER BY column (`joined_at`), so the rows come out already sorted. `chat_id`, the only selected column, goes last so the index **covers** the query. |
| HISTORY_PAGE | `(chat_id, created_at)` | Equality on `chat_id`, then the range `created_at < ?` on the next column. Walking the index backwards also gives `ORDER BY created_at DESC` for free, and `LIMIT 50` stops after 50 entries. |
| UNREAD_COUNT | the same index | `count(*)` needs no column values, and both filters are in the index, so SQLite never opens the table. |
| SENT_IN_CHAT | `(sender_id, chat_id)` | Two equalities, so either column order lets SQLite search on both. |

**What the tests rule out**

- `(created_at, chat_id)`: a range on the first column means the second can't be searched, and the sort stays.
- Adding both `(chat_id)` and `(chat_id, created_at)`: the shorter one is a prefix of the longer one, so it only costs
  writes. The SQLite query planner docs say exactly that: drop the index with fewer columns.
- Five or six single-purpose indexes: every index slows down every INSERT (L03 measures how much).

**Alternative:** `(chat_id, sender_id)` for SENT_IN_CHAT also passes. It shares `chat_id` as its first column with
`idx_messages_chat_created`, but neither is a prefix of the other, so both earn their place. Pick the order that also
serves another query you expect, for example "all messages by this user" (`sender_id` first).
