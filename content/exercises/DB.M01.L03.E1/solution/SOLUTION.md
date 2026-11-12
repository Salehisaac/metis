```sql
-- TOP_SENDERS
SELECT sender_id, count(*) AS messages
FROM messages
WHERE chat_id = :chat_id
  AND sent_at >= :start AND sent_at < :end
  AND trim(body) <> ''
GROUP BY sender_id
ORDER BY messages DESC, sender_id
LIMIT :n

-- DAILY_COUNTS
SELECT date(sent_at) AS day, count(*) AS messages
FROM messages
WHERE chat_id = :chat_id
GROUP BY day
HAVING count(*) >= :min_messages
ORDER BY day

-- ACTIVE_CHATS
SELECT chat_id, count(DISTINCT sender_id) AS senders, count(*) AS messages
FROM messages
WHERE sent_at >= :since
GROUP BY chat_id
ORDER BY senders DESC, chat_id
```

**Why it works**

- **WHERE runs before grouping, HAVING after.** The chat, the time range and "not blank" are facts about single messages, so they go in WHERE. "At least N messages that day" is a fact about a group, so it needs HAVING.
- **Half-open range.** `sent_at >= :start AND sent_at < :end` includes a message sent exactly at start and excludes one sent exactly at end. Consecutive ranges ([Mon, Tue), [Tue, Wed)) then never count a message twice or lose one. `BETWEEN` includes both ends; with an end of `'2026-11-08'` it also silently drops everything later on Nov 8, because `'2026-11-08 00:00:00' > '2026-11-08'` as text.
- **`trim(body) <> ''`.** `trim(X)` removes spaces from both ends, so a body of only spaces becomes `''`. Without it, user 2 gets 3 messages and ties with user 1.
- **Tie-breaks.** `ORDER BY messages DESC, sender_id` makes the order fully defined, so LIMIT always cuts at the same place.
- **`count(DISTINCT sender_id)`** counts different senders; `count(sender_id)` would count messages again (5 instead of 3 for chat 1).

**Alternatives and limits**

- `trim` only strips spaces. A body of only tabs or newlines would still count. `trim(body, ' ' || char(9) || char(10) || char(13))` strips those too, but it's usually better to validate at write time (DB.M02 shows CHECK constraints).
- `date(sent_at)` works because times are stored as UTC ISO text. "Per day" for a user in another time zone needs the time-zone conversion first; SQLite's date functions only know UTC and the machine's local time.
