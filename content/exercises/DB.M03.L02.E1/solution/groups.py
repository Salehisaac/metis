"""Creating a group chat: one chat row, one membership per person, and a first message.

The happy path works. But when a member id is wrong, the chat and some memberships are left behind,
half-created. Make create_group_chat all-or-nothing.
"""


def create_group_chat(conn, title, creator_id, member_ids, now):
    """Create a group chat and return its id.

    - The chat gets kind 'group', the title without surrounding spaces, and created_at = now.
    - The creator and every id in member_ids become members (joined_at = now). An id listed twice,
      or the creator listed again in member_ids, is added only once.
    - The creator posts the first message, body 'created the group', sent_at = now.
    - A blank title raises ValueError before anything is written.
    - If any step fails (e.g. an unknown user id raises sqlite3.IntegrityError), nothing at all is
      written, no transaction is left open, and the error reaches the caller.
    - On success everything is committed, so other connections see it.
    """
    title = title.strip()
    if not title:
        raise ValueError("title must not be blank")
    people = dict.fromkeys([creator_id, *member_ids])  # unique, first-seen order
    with conn:  # one transaction: commit if the block finishes, roll back if anything raises
        cur = conn.execute(
            "INSERT INTO chats (kind, title, created_at) VALUES ('group', ?, ?)", (title, now)
        )
        chat_id = cur.lastrowid
        for user_id in people:
            conn.execute(
                "INSERT INTO chat_members (chat_id, user_id, joined_at) VALUES (?, ?, ?)",
                (chat_id, user_id, now),
            )
        conn.execute(
            "INSERT INTO messages (chat_id, sender_id, body, sent_at) VALUES (?, ?, 'created the group', ?)",
            (chat_id, creator_id, now),
        )
    return chat_id
