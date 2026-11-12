---
{
  "id": "DB.M07.L04",
  "title": "Relationships, the N+1 problem and selectinload",
  "difficulty": "intermediate",
  "minutes": 80,
  "prerequisites": ["DB.M07.L03"],
  "objectives": [
    "Declare one-to-many, many-to-one and many-to-many relationships with relationship() and back_populates",
    "Explain lazy loading and count the statements an N+1 loop sends",
    "Fix N+1 with selectinload (collections) or joinedload (many-to-one), and verify it by counting statements",
    "Recognise DetachedInstanceError and use raiseload to make accidental lazy loads fail loudly"
  ],
  "why": "N+1 is the most common ORM performance bug, and it's invisible in tests with three rows: a list endpoint that's fast in development sends 501 queries in production. It's also why FastAPI responses sometimes crash with DetachedInstanceError. Both come from the same mechanism, lazy loading.",
  "applications": [
    "List endpoints that return objects with nested collections",
    "Serialising ORM objects into API responses after the session is closed",
    "Performance reviews: counting the queries a request sends"
  ],
  "exercises": ["DB.M07.L04.E1"],
  "sources": [
    {
      "title": "SQLAlchemy 2.1 Documentation: Relationship Loading Techniques",
      "url": "https://docs.sqlalchemy.org/en/21/orm/queryguide/relationships.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["Relationships are lazy-loaded by default, on first access", "Lazy loading N objects' related attributes means N+1 SELECTs", "selectinload emits a second SELECT with the parent primary keys in an IN clause and is generally the best strategy for collections", "joinedload adds a (LEFT OUTER) JOIN to the same SELECT", "raiseload raises instead of lazy loading, to catch unwanted loads"]
    },
    {
      "title": "SQLAlchemy 2.1 Documentation: Basic Relationship Patterns",
      "url": "https://docs.sqlalchemy.org/en/21/orm/basic_relationships.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["One-to-many puts the foreign key on the child table; Mapped[List['Child']] = relationship(back_populates=...)", "Many-to-many uses relationship(secondary=association_table) with a Core Table", "Bidirectional relationships name each other with back_populates"]
    },
    {
      "title": "SQLAlchemy 2.1 Documentation: Session Basics",
      "url": "https://docs.sqlalchemy.org/en/21/orm/session_basics.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["The identity map holds one object per primary key in a session"]
    }
  ]
}
---
## 1. Relationships: navigating with attributes

A `ForeignKey` (L01) describes the table. A `relationship()` lets Python code **navigate** it: `chat.messages`, `message.sender`.

```python
class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))

    messages: Mapped[list["Message"]] = relationship(back_populates="chat")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str]

    chat: Mapped["Chat"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship()
```

- **One-to-many** (`Chat.messages`): `Mapped[list[...]]`. The foreign key lives on the child table, `messages.chat_id`.
- **Many-to-one** (`Message.chat`, `Message.sender`): `Mapped["Chat"]`, a single object.
- **`back_populates`** names the attribute on the other side, so `chat.messages.append(m)` also sets `m.chat`.
- **Many-to-many** (chat members): the link table is a plain `Table`, and the relationship names it with `secondary=`, for example `members: Mapped[list[User]] = relationship(secondary=chat_members)`.
- Class names in quotes (`"Message"`) are fine when the class is defined further down.

Relationships add **no columns**. The DDL is the same as in L01; they only change what Python can do.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Which side of a chat ↔ messages one-to-many relationship holds the foreign key column?",
  "options": ["messages (chat_id references chats.id)", "chats (a message_ids column)", "Both", "Neither: relationship() stores it in a hidden table"], "answer": 0,
  "explanation": "The 'many' side, the child table, holds the foreign key. relationship() itself adds no columns." }
```

## 2. Lazy loading and N+1

By default a relationship loads **lazily**: the first time you touch `chat.messages`, SQLAlchemy sends a SELECT for that chat's messages. That's convenient, and it's a trap in loops. Five chats with three messages each; a hook counts every statement (SQLAlchemy 2.1.6, on this machine):

```python
def report(label, stmt):
    statements.clear()
    with Session(engine) as session:
        for chat in session.scalars(stmt):
            _ = [m.body for m in chat.messages]             # touch the relationship
    print(f"{label}: {len(statements)} SELECT statements")

report("lazy (default)", select(Chat))
report("selectinload  ", select(Chat).options(selectinload(Chat.messages)))
print(statements[1])
```

```console
lazy (default): 6 SELECT statements
selectinload  : 2 SELECT statements
SELECT messages.chat_id, messages.id, messages.sender_id, messages.body
FROM messages
WHERE messages.chat_id IN (?, ?, ?, ?, ?)
```

Lazy: **1** query for the chats **+ 1 per chat** for its messages. That's the **N+1 problem**. With 500 chats on a list page it's 501 round trips, and nothing in a 3-row test shows it.

`selectinload(Chat.messages)` tells the query up front: after loading the chats, fetch the messages of **all** of them in one `IN (...)` query. Two queries, whatever N is. The loop didn't change; only the loading strategy did. The docs call selectinload generally the best strategy for collections.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "4 teams with 2 players each. For each query, the code prints (total players, number of SQL statements sent). What does it print?",
  "code": "from sqlalchemy import ForeignKey, create_engine, event, select\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, selectinload\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Team(Base):\n    __tablename__ = 'teams'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    players: Mapped[list['Player']] = relationship()\n\nclass Player(Base):\n    __tablename__ = 'players'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    team_id: Mapped[int] = mapped_column(ForeignKey('teams.id'))\n\nengine = create_engine('sqlite://')\nBase.metadata.create_all(engine)\nwith Session(engine) as s, s.begin():\n    s.add_all([Team(players=[Player(), Player()]) for _ in range(4)])\nsent = []\nevent.listen(engine, 'before_cursor_execute', lambda *a: sent.append(a[2]))\nfor stmt in (select(Team), select(Team).options(selectinload(Team.players))):\n    sent.clear()\n    with Session(engine) as s:\n        total = sum(len(t.players) for t in s.scalars(stmt))\n    print(total, len(sent))",
  "answer": "8 5\n8 2",
  "explanation": "Same 8 players both times. Lazy: 1 query for the teams plus 1 per team = 5. selectinload: the teams, then all their players in one IN query = 2." }
```

## 3. Many-to-one: joinedload, and the identity map

Now the other direction: each message's sender (15 messages, 3 distinct senders):

```python
senders("lazy      ", select(Message))
senders("joinedload", select(Message).options(joinedload(Message.sender)))
print(statements[0])
```

```console
lazy      : 15 messages, 4 SELECT statements
joinedload: 15 messages, 1 SELECT statements
SELECT messages.id, messages.chat_id, messages.sender_id, messages.body, users_1.id AS id_1, users_1.username
FROM messages LEFT OUTER JOIN users AS users_1 ON users_1.id = messages.sender_id
```

- Lazy was 4, not 16: once a sender is in the session's **identity map** (L02), `message.sender` for the same user needs no query. N+1 is really "1 + the number of distinct related objects not loaded yet", which is why it hides in small test data and explodes with real users.
- **`joinedload`** adds a LEFT OUTER JOIN to the same SELECT: one query. It fits many-to-one well (one sender per message row). For collections, a join repeats the parent row once per child, and with `LIMIT` it limits joined rows rather than parents, so prefer `selectinload` there.

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "A list endpoint returns 50 orders, each with its customer (many-to-one) and its line items (one-to-many). Which loader options fit best?",
  "options": ["joinedload(Order.customer) and selectinload(Order.items)", "selectinload for nothing; lazy loading is fine", "joinedload for both", "Load everything with select(Customer) instead"], "answer": 0,
  "explanation": "A join suits the single customer per order. For the collection, selectinload avoids multiplying order rows and stays correct with LIMIT 50." }
```

## 4. Lazy loading after the session is gone

The same mechanism causes a classic FastAPI crash: you load objects, the request's session closes, then the response serialiser touches a relationship.

```python
with Session(engine) as session:
    chat = session.scalars(select(Chat).options(raiseload(Chat.messages))).first()
    try:
        chat.messages
    except Exception as e:
        print(type(e).__name__, ":", e)

with Session(engine) as session:
    chat = session.scalars(select(Chat)).first()
try:
    chat.messages          # session is closed now
except Exception as e:
    print(type(e).__name__, ":", str(e)[:95])
```

```console
InvalidRequestError : 'Chat.messages' is not available due to lazy='raise'
DetachedInstanceError : Parent instance <Chat at 0x7dc9f2184e00> is not bound to a Session; lazy load operation of attr
```

- **`DetachedInstanceError`**: there's no session left to run the lazy SELECT. The fix isn't "keep the session open longer"; it's to **load what the response needs inside the request**, with `selectinload` / `joinedload`.
- **`raiseload`** turns every would-be lazy load into an immediate error. Put it on read models (or `raiseload("*")` in tests) and N+1 can't sneak back in silently.

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "If a FastAPI endpoint raises DetachedInstanceError while building its response, the best fix is to keep the database session open until the response has been sent.", "answer": false,
  "explanation": "That hides the problem and still sends one lazy query per object. Load the relationships the response needs inside the request with eager loading options." }
```

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "A test seeds 3 chats and passes quickly. In production the same endpoint is slow, and the query log shows the same `SELECT ... FROM users WHERE users.id = ?` repeated hundreds of times per request. What's the most likely cause?",
  "options": ["A loop touches a lazy many-to-one relationship (e.g. message.sender) for many distinct users", "The users table is missing a primary key", "The session's identity map is disabled", "SQLite doesn't support joins"], "answer": 0,
  "explanation": "Lazy loading sends one SELECT per not-yet-loaded related object. With 3 seeded rows it's invisible; with real data it's hundreds. joinedload or selectinload fixes it." }
```

## 5. Your turn

The chat-list screen's two functions return the right data, and their content tests already pass. But they lazy-load inside loops. Count the SELECTs (the tests do), then make each function send at most two, without changing what it returns.

```exercise
DB.M07.L04.E1
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "How would you catch N+1 problems before production in a FastAPI project? Name two concrete techniques.",
  "model": "1) In tests, count the SQL statements per endpoint with an engine event (before_cursor_execute) on seeded data with many rows and many distinct related objects, and assert an upper bound. 2) Use raiseload('*') (or lazy='raise') on read paths so any accidental lazy load fails the test immediately. Also: log SQL with echo in development and look for repeated identical SELECTs.",
  "explanation": "Make the query count visible and bounded; make accidental lazy loads fail loudly." }
```
