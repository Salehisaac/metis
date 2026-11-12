```sql
-- CHAT_LIST
SELECT c.id,
       c.title,
       (SELECT count(*) FROM chat_members AS all_m WHERE all_m.chat_id = c.id) AS members,
       (SELECT count(*) FROM messages AS m WHERE m.chat_id = c.id) AS messages,
       (SELECT max(m.sent_at) FROM messages AS m WHERE m.chat_id = c.id) AS last_message_at
FROM chat_members AS me
JOIN chats AS c ON c.id = me.chat_id
WHERE me.user_id = ?
ORDER BY last_message_at DESC NULLS LAST, c.id

-- LATEST_PER_CHAT
SELECT m.chat_id, m.id, u.username, m.body
FROM messages AS m
JOIN users AS u ON u.id = m.sender_id
WHERE m.id = (
    SELECT newest.id
    FROM messages AS newest
    WHERE newest.chat_id = m.chat_id
    ORDER BY newest.sent_at DESC, newest.id DESC
    LIMIT 1
)
ORDER BY m.chat_id
```

**Why it works**

- **The outer query has one row per chat of this user.** `chat_members AS me` filtered to the user gives exactly one row per chat (the primary key guarantees it). Nothing else is joined, so nothing multiplies.
- **Each number comes from its own correlated subquery,** which runs once per outer row and sees only that chat. Joining both chat_members and messages instead gives chat 1 a group of 3 x 10 = 30 rows, and both counts come out as 30.
- **`count(*)` is right inside the subqueries,** because they only see matching rows; for a chat with no messages, count is 0 and max is NULL.
- **`DESC NULLS LAST`** states the intent. SQLite already puts NULLs last in a DESC sort (they sort as smallest), but other databases differ.
- **Latest message per chat:** `max(sent_at)` with bare columns would take message 15 or 16 arbitrarily, because they share the newest sent_at (in this run SQLite returned 15). The subquery orders by `sent_at DESC, id DESC` and takes exactly one id per chat.

**Alternatives**

- `count(DISTINCT cm.user_id)` and `count(DISTINCT m.id)` after joining both tables give the same numbers here, but the database still builds the multiplied rows first, and `DISTINCT` doesn't help with `sum()` (two equal amounts are not duplicates).
- Pre-aggregate in derived tables: `LEFT JOIN (SELECT chat_id, count(*) AS n, max(sent_at) AS last FROM messages GROUP BY chat_id) AS stats ON stats.chat_id = c.id`. Each derived table has one row per chat, so joining it can't fan out. This is often faster than correlated subqueries on big tables.
- Window function: `row_number() OVER (PARTITION BY chat_id ORDER BY sent_at DESC, id DESC) AS rn` in a subquery, then `WHERE rn = 1`. SQLite supports window functions since 3.25.0.
