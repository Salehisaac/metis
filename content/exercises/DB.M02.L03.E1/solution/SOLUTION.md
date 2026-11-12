```sql
-- MESSAGES_PER_USER
SELECT u.username, count(m.id) AS messages
FROM users AS u
LEFT JOIN messages AS m ON m.sender_id = u.id
GROUP BY u.id, u.username
ORDER BY messages DESC, u.username

-- SILENT_MEMBERS
SELECT u.username
FROM chat_members AS cm
JOIN users AS u ON u.id = cm.user_id
LEFT JOIN messages AS m ON m.chat_id = cm.chat_id AND m.sender_id = cm.user_id
WHERE cm.chat_id = ? AND m.id IS NULL
ORDER BY u.username

-- CHAT_ACTIVITY_SINCE
SELECT c.id, count(m.id) AS messages
FROM chats AS c
LEFT JOIN messages AS m ON m.chat_id = c.id AND m.sent_at >= ?
GROUP BY c.id
ORDER BY c.id
```

**Why it works**

- **`count(m.id)`, not `count(*)`.** dara has no messages, so the LEFT JOIN gives her one row with NULL in every messages column. `count(*)` counts that row (1); `count(m.id)` counts only non-NULL ids (0).
- **The time filter belongs in ON.** With `WHERE m.sent_at >= ?`, the NULL rows of chats without recent messages fail the test (NULL >= x is NULL) and chats 2 and 4 vanish: the LEFT JOIN is silently turned into an INNER JOIN. In ON, the condition decides *which messages match*; chats with no matching message still get their NULL row.
- **The anti-join needs the chat in ON.** `ON m.sender_id = cm.user_id` alone would match ana's messages in chats 1 and 2, so she wouldn't look silent in chat 3. Matching on both chat and sender, then keeping `m.id IS NULL`, leaves exactly the members with no message in that chat.
- **`GROUP BY u.id, u.username`.** Grouping by id keeps two users with the same name apart (not possible here, since username is UNIQUE, but a good habit), and username is listed so that no selected column is bare.

**Alternatives**

- SILENT_MEMBERS with `NOT EXISTS (SELECT 1 FROM messages AS m WHERE m.chat_id = cm.chat_id AND m.sender_id = cm.user_id)`. Many people find this reads closer to the English. Both are correct.
- MESSAGES_PER_USER with a correlated subquery: `SELECT u.username, (SELECT count(*) FROM messages AS m WHERE m.sender_id = u.id) AS messages FROM users AS u ...`. Here `count(*)` is right, because the subquery only sees matching messages.
