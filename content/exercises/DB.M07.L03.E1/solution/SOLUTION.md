```python
def find_user(session, username):
    return session.scalars(select(User).where(User.username == username)).one_or_none()


def messages_page(session, chat_id, before_id=None, limit=20):
    stmt = select(Message).where(Message.chat_id == chat_id)
    if before_id is not None:
        stmt = stmt.where(Message.id < before_id)
    return list(session.scalars(stmt.order_by(Message.id.desc()).limit(limit)))


def member_counts(session):
    member_count = func.count(ChatMember.user_id)
    stmt = (
        select(Chat.title, member_count)
        .outerjoin(ChatMember, ChatMember.chat_id == Chat.id)
        .group_by(Chat.id)
        .order_by(member_count.desc(), Chat.title)
    )
    return [(title, count) for title, count in session.execute(stmt)]


def like(session, message_id):
    result = session.execute(
        update(Message).where(Message.id == message_id).values(likes=Message.likes + 1)
    )
    if result.rowcount == 0:
        raise LookupError(f"no message {message_id}")
```

**Why it works**

- `one_or_none()` returns the object or `None`, and raises if there are several rows: a useful guard on a column
  that's supposed to be unique. `.first()` would silently hide a duplicate.
- `messages_page` builds the statement step by step: a `Select` is immutable, and each `.where()` returns a new one
  with the conditions ANDed. This is **keyset pagination**: "older than the last id I saw" stays correct when new
  messages arrive, unlike `OFFSET`, which shifts. With an index on the chat it's also a cheap range lookup (DB.M05).
- `member_counts` needs a **LEFT OUTER JOIN** so that a chat without members still produces one row (DB.M02), and
  `count(ChatMember.user_id)` counts only non-NULL values, so that row counts 0. `count(*)` would give 1.
  The second `order_by` key is the tie-break (equal counts, then title).
- `like` sends `likes = likes + 1` to the database instead of loading the object and changing the attribute, which
  would send a fixed value: two concurrent likes would both write the same number and one would be lost. `rowcount` reports how many rows matched.

**Alternative:** `select(Chat.title, func.count(ChatMember.user_id)).join(ChatMember, isouter=True)` is the same
outer join written with `join()`.
