"""The two queries behind a messenger's home screen.

The tests run each query with ? parameters against chatdb.make_db().
"""

# The chat list of one user: every chat they are a member of, with
#   members          how many members the chat has (all of them, not just this user)
#   messages         how many messages the chat has (0 if none)
#   last_message_at  sent_at of the chat's newest message (None if none)
# Columns: (chat_id, title, members, messages, last_message_at).
# Order: most recent activity first; chats without messages last; ties by chat_id.
# Parameters: (user_id,)
CHAT_LIST = """
SELECT c.id,
       c.title,
       (SELECT count(*) FROM chat_members AS all_m WHERE all_m.chat_id = c.id) AS members,
       (SELECT count(*) FROM messages AS m WHERE m.chat_id = c.id) AS messages,
       (SELECT max(m.sent_at) FROM messages AS m WHERE m.chat_id = c.id) AS last_message_at
FROM chat_members AS me
JOIN chats AS c ON c.id = me.chat_id
WHERE me.user_id = ?
ORDER BY last_message_at DESC NULLS LAST, c.id
"""

# The newest message of every chat that has messages ("newest": latest sent_at, then highest id).
# Columns: (chat_id, message_id, sender's username, body). Ordered by chat_id.
# Parameters: none
LATEST_PER_CHAT = """
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
"""
