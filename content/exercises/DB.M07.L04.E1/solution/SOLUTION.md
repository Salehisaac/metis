```python
def chat_member_lists(session):
    stmt = select(Chat).options(selectinload(Chat.members)).order_by(Chat.title)
    result = []
    for chat in session.scalars(stmt):
        result.append((chat.title, sorted(user.username for user in chat.members)))
    return result


def latest_with_senders(session, chat_id, limit=10):
    stmt = (
        select(Message)
        .options(joinedload(Message.sender))
        .where(Message.chat_id == chat_id)
        .order_by(Message.id.desc())
        .limit(limit)
    )
    return [(message.sender.username, message.body) for message in session.scalars(stmt)]
```

**What was wrong:** relationships load lazily by default. Each `chat.members` and each `message.sender` the loop
touched sent its own SELECT: 1 query for the chats plus 1 per chat (N+1), and 1 for the messages plus 1 per
not-yet-loaded sender.

**Why the fix works**

- `selectinload(Chat.members)` loads the members of **all** returned chats with one extra
  `SELECT ... WHERE chat_id IN (...)`: 2 queries, however many chats there are. The SQLAlchemy docs call it generally
  the best strategy for collections.
- `joinedload(Message.sender)` adds a `LEFT OUTER JOIN users` to the same SELECT, so each row arrives with its
  sender: 1 query. That suits a many-to-one, where the join adds one user per message row and never multiplies rows.
  (`selectinload(Message.sender)` also passes the test, with 2 queries.)
- The loop bodies didn't change at all: the fix is *how* the relationship gets loaded, chosen at query time.

**Why not joinedload for members?** Joining a collection repeats each chat's columns once per member, and combined
with `LIMIT` it limits joined rows, not chats. `selectinload` avoids both.

**Guard against regressions:** `raiseload("*")` in tests or in a read model makes any accidental lazy load raise
instead of silently adding queries.
