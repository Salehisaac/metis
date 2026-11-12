"""Chat statistics. Each constant is one SELECT that uses named placeholders (:name).

The tests pass the parameters as a dict, e.g. {"chat_id": 1, "start": "...", "end": "...", "n": 2}.
"""

# Top senders in one chat within a time range [start, end): start included, end excluded.
# Count only messages whose body isn't blank (only spaces counts as blank).
# Columns: (sender_id, messages). Most messages first; ties: lower sender_id first. At most n rows.
# Parameters: :chat_id, :start, :end, :n
TOP_SENDERS = """
-- TODO
"""

# Messages per calendar day in one chat (all messages, blank or not), only for days with at least :min_messages.
# Columns: (day, messages) where day looks like '2026-11-02'. Ordered by day.
# Parameters: :chat_id, :min_messages
DAILY_COUNTS = """
-- TODO
"""

# Per chat, activity since a moment (sent_at >= :since): how many different people wrote, and how many messages.
# Columns: (chat_id, senders, messages). Most senders first; ties: lower chat_id first.
# Chats with no messages in that period don't appear.
# Parameters: :since
ACTIVE_CHATS = """
-- TODO
"""
