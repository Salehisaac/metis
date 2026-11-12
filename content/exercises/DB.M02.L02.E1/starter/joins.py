"""Queries that need data from more than one table. Use JOIN ... ON and table aliases.

The tests run each query with ? parameters against chatdb.make_db().
"""

# The transcript of one chat: (message id, sender's username, body), oldest first (sent_at, then id).
# Parameters: (chat_id,)
CHAT_TRANSCRIPT = """
-- TODO
"""

# Usernames (username,) of the members of one chat, alphabetical.
# Parameters: (chat_id,)
CHAT_MEMBER_NAMES = """
-- TODO
"""

# Messages written by the user with this username: (message id, chat_id), ordered by message id.
# Parameters: (username,)
MESSAGES_BY_USERNAME = """
-- TODO
"""

# Chats (chat_id,) that both users are members of, ordered by chat_id.
# Parameters: (user_a, user_b)
SHARED_CHATS = """
-- TODO
"""
