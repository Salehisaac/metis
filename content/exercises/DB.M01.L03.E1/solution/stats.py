"""Chat statistics. Each constant is one SELECT that uses named placeholders (:name).

The tests pass the parameters as a dict, e.g. {"chat_id": 1, "start": "...", "end": "...", "n": 2}.
"""

# Top senders in one chat within a time range [start, end): start included, end excluded.
# Count only messages whose body isn't blank (only spaces counts as blank).
# Columns: (sender_id, messages). Most messages first; ties: lower sender_id first. At most n rows.
# Parameters: :chat_id, :start, :end, :n
TOP_SENDERS = """
SELECT sender_id, count(*) AS messages
FROM messages
WHERE chat_id = :chat_id
  AND sent_at >= :start AND sent_at < :end
  AND trim(body) <> ''
GROUP BY sender_id
ORDER BY messages DESC, sender_id
LIMIT :n
"""

# Messages per calendar day in one chat (all messages, blank or not), only for days with at least :min_messages.
# Columns: (day, messages) where day looks like '2026-11-02'. Ordered by day.
# Parameters: :chat_id, :min_messages
DAILY_COUNTS = """
SELECT date(sent_at) AS day, count(*) AS messages
FROM messages
WHERE chat_id = :chat_id
GROUP BY day
HAVING count(*) >= :min_messages
ORDER BY day
"""

# Per chat, activity since a moment (sent_at >= :since): how many different people wrote, and how many messages.
# Columns: (chat_id, senders, messages). Most senders first; ties: lower chat_id first.
# Chats with no messages in that period don't appear.
# Parameters: :since
ACTIVE_CHATS = """
SELECT chat_id, count(DISTINCT sender_id) AS senders, count(*) AS messages
FROM messages
WHERE sent_at >= :since
GROUP BY chat_id
ORDER BY senders DESC, chat_id
"""
