"""Leaving a chat. This implementation is correct; your job is to write the tests that prove it.

Don't edit this file.
"""


class NotAMember(Exception):
    """The user isn't a member of that chat."""


def leave_chat(conn, chat_id, user_id, now):
    """The user leaves the chat, as one transaction:

    - posts a message from the user with body 'left the chat' and sent_at = now
    - removes the user's membership of this chat (and of no other chat)

    If the user isn't a member of the chat, raises NotAMember and writes nothing.
    On success both changes are committed.
    """
    with conn:
        conn.execute(
            "INSERT INTO messages (chat_id, sender_id, body, sent_at) VALUES (?, ?, 'left the chat', ?)",
            (chat_id, user_id, now),
        )
        cur = conn.execute(
            "DELETE FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)
        )
        if cur.rowcount == 0:
            raise NotAMember(f"user {user_id} is not a member of chat {chat_id}")
