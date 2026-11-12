"""Queries that need data from more than one table. Use JOIN ... ON and table aliases.

The tests run each query with ? parameters against chatdb.make_db().
"""

# The transcript of one chat: (message id, sender's username, body), oldest first (sent_at, then id).
# Parameters: (chat_id,)
CHAT_TRANSCRIPT = """
SELECT m.id, u.username, m.body
FROM messages AS m
JOIN users AS u ON u.id = m.sender_id
WHERE m.chat_id = ?
ORDER BY m.sent_at, m.id
"""

# Usernames (username,) of the members of one chat, alphabetical.
# Parameters: (chat_id,)
CHAT_MEMBER_NAMES = """
SELECT u.username
FROM chat_members AS cm
JOIN users AS u ON u.id = cm.user_id
WHERE cm.chat_id = ?
ORDER BY u.username
"""

# Messages written by the user with this username: (message id, chat_id), ordered by message id.
# Parameters: (username,)
MESSAGES_BY_USERNAME = """
SELECT m.id, m.chat_id
FROM messages AS m
JOIN users AS u ON u.id = m.sender_id
WHERE u.username = ?
ORDER BY m.id
"""

# Chats (chat_id,) that both users are members of, ordered by chat_id.
# Parameters: (user_a, user_b)
SHARED_CHATS = """
SELECT a.chat_id
FROM chat_members AS a
JOIN chat_members AS b ON b.chat_id = a.chat_id
WHERE a.user_id = ? AND b.user_id = ?
ORDER BY a.chat_id
"""
