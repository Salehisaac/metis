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
-- TODO
"""

# The newest message of every chat that has messages ("newest": latest sent_at, then highest id).
# Columns: (chat_id, message_id, sender's username, body). Ordered by chat_id.
# Parameters: none
LATEST_PER_CHAT = """
-- TODO
"""
