"""Indexes for the messenger's hot queries (see test_inbox_indexes.py for the queries).

Each entry is one CREATE INDEX statement. Name them idx_<table>_<columns>.
The tables already have the indexes created by their PRIMARY KEY and UNIQUE constraints.
"""

INDEXES: list[str] = [
    # MY_CHATS: equality on user_id, then ORDER BY joined_at; chat_id at the end makes it covering.
    "CREATE INDEX idx_chat_members_user_joined_chat ON chat_members (user_id, joined_at, chat_id)",
    # HISTORY_PAGE and UNREAD_COUNT: equality on chat_id, then a range and ORDER BY on created_at.
    "CREATE INDEX idx_messages_chat_created ON messages (chat_id, created_at)",
    # SENT_IN_CHAT: two equalities, so either order works for this query.
    "CREATE INDEX idx_messages_sender_chat ON messages (sender_id, chat_id)",
]
