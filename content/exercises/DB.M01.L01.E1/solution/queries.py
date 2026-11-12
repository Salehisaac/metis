"""Your SQL goes here. Each constant is one query; the tests run it with the parameters shown.

Use ? placeholders for the values; never paste values into the string.
"""

# Messages (id, body) sent by one sender that were never edited, oldest id first.
# Parameters: (sender_id,)
UNEDITED_BY_SENDER = """
SELECT id, body
FROM messages
WHERE sender_id = ? AND edited_at IS NULL
ORDER BY id
"""

# The n most recent messages (id, sent_at) in one chat, newest first.
# Two messages with the same sent_at: the higher id comes first.
# Parameters: (chat_id, n)
LATEST_IN_CHAT = """
SELECT id, sent_at
FROM messages
WHERE chat_id = ?
ORDER BY sent_at DESC, id DESC
LIMIT ?
"""

# Ids (id,) of the messages in one chat sent by either of two users, ordered by id.
# Parameters: (chat_id, user_a, user_b)
IN_CHAT_FROM_EITHER = """
SELECT id
FROM messages
WHERE chat_id = ? AND (sender_id = ? OR sender_id = ?)
ORDER BY id
"""

# One page of usernames (username,) in alphabetical order.
# Parameters: (page_size, rows_to_skip)
USERS_PAGE = """
SELECT username
FROM users
ORDER BY username
LIMIT ? OFFSET ?
"""
