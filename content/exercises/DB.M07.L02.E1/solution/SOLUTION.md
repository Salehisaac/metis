```python
def create_group(session_factory, title, creator, members):
    if not title.strip():
        raise ValueError("title must not be blank")
    wanted = list(dict.fromkeys([creator, *members]))  # unique, order kept
    with session_factory.begin() as session:
        found = session.scalars(select(User).where(User.username.in_(wanted))).all()
        by_name = {u.username: u for u in found}
        missing = [name for name in wanted if name not in by_name]
        if missing:
            raise LookupError(f"unknown users: {', '.join(missing)}")
        chat = Chat(title=title)
        session.add(chat)
        session.flush()  # INSERT now, so chat.id is known
        session.add_all([ChatMember(chat_id=chat.id, user_id=by_name[name].id) for name in wanted])
        return chat.id


def add_member(session_factory, chat_id, username):
    with session_factory.begin() as session:
        if session.get(Chat, chat_id) is None:
            raise LookupError(f"no chat {chat_id}")
        user = session.scalars(select(User).where(User.username == username)).one_or_none()
        if user is None:
            raise LookupError(f"no user {username}")
        if session.get(ChatMember, (chat_id, user.id)) is not None:
            return False
        session.add(ChatMember(chat_id=chat_id, user_id=user.id))
        return True
```

**Why it works**

- `session_factory.begin()` is "begin once": it opens a session and a transaction, **commits when the block ends
  normally and rolls back if anything raises**. Raising `LookupError` inside the block is therefore enough to undo
  everything, so no manual `rollback()` and no half-created chat.
- All usernames are looked up with **one** `IN` query, and the missing ones are computed from the result. You can
  name every unknown user, and validation happens before any INSERT.
- `session.flush()` sends the pending INSERT for the chat inside the open transaction, so `chat.id` is filled in
  (SQLite returns it via `RETURNING`). It is **not** a commit: a later exception still rolls it back.
- `return chat.id` inside the `with` reads the id *before* the commit happens on exit. After commit the object is
  expired (`expire_on_commit`), and with the session closed you couldn't reload it.
- `dict.fromkeys([...])` removes duplicates and keeps the order.
- `session.get(ChatMember, (chat_id, user.id))` looks up a composite primary key with a tuple in column order.

**Alternative for add_member:** insert unconditionally and catch `IntegrityError` for the duplicate primary key. That
avoids a check-then-insert race between two concurrent requests (both check, both insert), at the cost of using an exception for a
normal outcome. DB.M08 shows a third way: `INSERT ... ON CONFLICT DO NOTHING`.
