"""Three write statements from a chat backend. Each one has a bug that a code review missed.

Fix the SQL so the tests pass. Keep the parameters (the order shown in each comment) unchanged.
"""

# Register a new user; the database assigns the id.
# Parameters: (username, created_at)
ADD_USER = """
INSERT INTO users VALUES (?, ?)
"""

# Edit one message's text and record when it was edited.
# Parameters: (new_body, edited_at, message_id)
EDIT_MESSAGE = """
UPDATE messages SET body = ?, edited_at = ?
"""

# One user leaves one chat.
# Parameters: (chat_id, user_id)
LEAVE_CHAT = """
DELETE FROM chat_members WHERE chat_id = ? OR user_id = ?
"""
