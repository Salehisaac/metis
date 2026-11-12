```sql
-- CHAT_TRANSCRIPT
SELECT m.id, u.username, m.body
FROM messages AS m
JOIN users AS u ON u.id = m.sender_id
WHERE m.chat_id = ?
ORDER BY m.sent_at, m.id

-- CHAT_MEMBER_NAMES
SELECT u.username
FROM chat_members AS cm
JOIN users AS u ON u.id = cm.user_id
WHERE cm.chat_id = ?
ORDER BY u.username

-- MESSAGES_BY_USERNAME
SELECT m.id, m.chat_id
FROM messages AS m
JOIN users AS u ON u.id = m.sender_id
WHERE u.username = ?
ORDER BY m.id

-- SHARED_CHATS
SELECT a.chat_id
FROM chat_members AS a
JOIN chat_members AS b ON b.chat_id = a.chat_id
WHERE a.user_id = ? AND b.user_id = ?
ORDER BY a.chat_id
```

**Why it works**

- **One result row per row of the "many" side.** Each message matches exactly one user (sender_id is NOT NULL and a foreign key), so the transcript has exactly as many rows as the chat has messages. The join only *adds columns*.
- **Aliases are required** once two tables share column names (`id` is in both messages and users). Unqualified `id` is an error: "ambiguous column name: id".
- **The self-join** treats chat_members as two separate inputs. Each output row pairs a membership of user a with a membership of user b in the same chat, so a row exists exactly when both are members.

**Alternatives**

- SHARED_CHATS with set logic: `SELECT chat_id FROM chat_members WHERE user_id = ? INTERSECT SELECT chat_id FROM chat_members WHERE user_id = ? ORDER BY chat_id`. Also correct, and arguably clearer.
- SHARED_CHATS with grouping: `WHERE user_id IN (?, ?) GROUP BY chat_id HAVING count(*) = 2`. This relies on (chat_id, user_id) being the primary key; without that rule, a duplicated membership would fake a match. It also differs from the join when both parameters are the same user: it returns no chats, while the self-join returns all of that user's chats.
- MESSAGES_BY_USERNAME with a subquery: `WHERE m.sender_id = (SELECT id FROM users WHERE username = ?)`. Same result, because username is UNIQUE.
