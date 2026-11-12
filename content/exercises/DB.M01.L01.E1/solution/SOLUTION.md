```sql
-- UNEDITED_BY_SENDER
SELECT id, body
FROM messages
WHERE sender_id = ? AND edited_at IS NULL
ORDER BY id

-- LATEST_IN_CHAT
SELECT id, sent_at
FROM messages
WHERE chat_id = ?
ORDER BY sent_at DESC, id DESC
LIMIT ?

-- IN_CHAT_FROM_EITHER
SELECT id
FROM messages
WHERE chat_id = ? AND (sender_id = ? OR sender_id = ?)
ORDER BY id

-- USERS_PAGE
SELECT username
FROM users
ORDER BY username
LIMIT ? OFFSET ?
```

**Why it works**

- **`IS NULL`:** `edited_at = NULL` evaluates to NULL for every row, and WHERE keeps only rows where the condition is true, so it returns nothing. `IS NULL` is the operator that can be true for NULL.
- **Two sort keys:** `ORDER BY sent_at DESC` alone leaves messages 15 and 16 (same second) in an undefined order. In practice SQLite returned 15 before 16 here, which fails the test. `id DESC` makes the order fully defined.
- **Parentheses:** AND binds tighter than OR. Without parentheses the WHERE reads `(chat_id = ? AND sender_id = ?) OR sender_id = ?`, which pulls in user 1's messages from chat 2 (ids 4 and 12).
- **LIMIT/OFFSET:** a LIMIT larger than the result returns everything; an OFFSET past the end returns no rows. Neither is an error.

**Alternatives**

- `sender_id IN (?, ?)` is equivalent to the parenthesised OR and avoids the precedence trap entirely.
- OFFSET pagination re-reads and skips rows, so deep pages get slower, and rows inserted between requests shift the pages. Keyset pagination (`WHERE username > ? ORDER BY username LIMIT ?`, passing the last username you saw) avoids both. DB.M05 (indexes) returns to this.
