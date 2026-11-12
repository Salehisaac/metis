"""Queries where rows without a match must still appear (or must be found). Use LEFT JOIN.

The tests run each query with ? parameters against chatdb.make_db().
"""

# Every user with the number of messages they've sent, including users who sent none (0).
# Columns: (username, messages). Most messages first; ties: username alphabetical.
# Parameters: none
MESSAGES_PER_USER = """
-- TODO
"""

# Members of one chat who have never posted in that chat (messages in other chats don't count).
# Columns: (username,). Alphabetical.
# Parameters: (chat_id,)
SILENT_MEMBERS = """
-- TODO
"""

# Every chat with the number of its messages sent at or after a moment; chats with none show 0.
# Columns: (chat_id, messages). Ordered by chat_id.
# Parameters: (since,)
CHAT_ACTIVITY_SINCE = """
-- TODO
"""
