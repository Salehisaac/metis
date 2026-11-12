"""Queries where rows without a match must still appear (or must be found). Use LEFT JOIN.

The tests run each query with ? parameters against chatdb.make_db().
"""

# Every user with the number of messages they've sent, including users who sent none (0).
# Columns: (username, messages). Most messages first; ties: username alphabetical.
# Parameters: none
MESSAGES_PER_USER = """
SELECT u.username, count(m.id) AS messages
FROM users AS u
LEFT JOIN messages AS m ON m.sender_id = u.id
GROUP BY u.id, u.username
ORDER BY messages DESC, u.username
"""

# Members of one chat who have never posted in that chat (messages in other chats don't count).
# Columns: (username,). Alphabetical.
# Parameters: (chat_id,)
SILENT_MEMBERS = """
SELECT u.username
FROM chat_members AS cm
JOIN users AS u ON u.id = cm.user_id
LEFT JOIN messages AS m ON m.chat_id = cm.chat_id AND m.sender_id = cm.user_id
WHERE cm.chat_id = ? AND m.id IS NULL
ORDER BY u.username
"""

# Every chat with the number of its messages sent at or after a moment; chats with none show 0.
# Columns: (chat_id, messages). Ordered by chat_id.
# Parameters: (since,)
CHAT_ACTIVITY_SINCE = """
SELECT c.id, count(m.id) AS messages
FROM chats AS c
LEFT JOIN messages AS m ON m.chat_id = c.id AND m.sent_at >= ?
GROUP BY c.id
ORDER BY c.id
"""
