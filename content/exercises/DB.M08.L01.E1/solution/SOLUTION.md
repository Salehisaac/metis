```sql
CREATE TABLE users (
    id       INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE
);

CREATE TABLE chats (
    id    INTEGER PRIMARY KEY,
    kind  TEXT NOT NULL CONSTRAINT chk_chats_kind CHECK (kind IN ('direct', 'group')),
    title TEXT,
    CONSTRAINT chk_chats_group_has_title CHECK (kind = 'direct' OR title IS NOT NULL)
);

CREATE TABLE chat_members (
    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    role    TEXT NOT NULL DEFAULT 'member'
            CONSTRAINT chk_chat_members_role CHECK (role IN ('owner', 'admin', 'member')),
    PRIMARY KEY (chat_id, user_id)
);
```

and in `connect()`: `conn.execute("PRAGMA foreign_keys = ON")` before anything else.

**Why it works**

- `NOT NULL` is needed next to every `CHECK`: a CHECK passes when its expression is NULL, so
  `CHECK (kind IN (...))` alone would let `kind = NULL` through. The same goes for `role`.
- "A group must have a title" involves two columns, so it's a **table-level** CHECK:
  `kind = 'direct' OR title IS NOT NULL`. Read it as "if it's not direct, the title must be there".
- `ON DELETE CASCADE` on `chat_id` deletes memberships with their chat. `user_id` has no action, so the default
  (NO ACTION) refuses to delete a user who is still referenced.
- SQLite ignores all foreign keys unless `PRAGMA foreign_keys = ON` runs **on each connection**. Without it the
  REFERENCES clauses are decoration. PostgreSQL always enforces them.
- `CONSTRAINT name` gives readable errors (`CHECK constraint failed: chk_chats_kind`) and lets a migration drop
  or change the rule later.

**Alternative:** a lookup table `chat_kinds(kind TEXT PRIMARY KEY)` with a foreign key instead of the IN list. It's
more flexible when values are added often; for a fixed set of two, the CHECK is simpler.
