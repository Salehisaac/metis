---
{
  "id": "DB.M07.L03",
  "title": "Querying with select(): filters, joins, aggregates and bulk updates",
  "difficulty": "intermediate",
  "minutes": 85,
  "prerequisites": ["DB.M07.L02"],
  "objectives": [
    "Translate SELECT ... WHERE ... ORDER BY ... LIMIT into select() and print the SQL it generates",
    "Choose between session.scalars() (objects or one column) and session.execute() (rows of several columns), and between one(), one_or_none() and all()",
    "Write JOINs and GROUP BY aggregates with select(), using an outer join when zero counts must appear",
    "Send UPDATE ... SET x = x + 1 with update().values() instead of a read-modify-write through an object"
  ],
  "why": "You can already write this SQL by hand. The point here is to write it in the form your future codebases use, while still knowing exactly which SQL goes out, so the JOIN row-count rules from DB.M02 survive the move to an ORM, and counters don't silently lose updates.",
  "applications": [
    "Repository functions behind FastAPI endpoints",
    "Paginated feeds and dashboards with counts",
    "Counters and other updates that must not lose concurrent writes"
  ],
  "exercises": ["DB.M07.L03.E1"],
  "sources": [
    {
      "title": "SQLAlchemy Unified Tutorial: Using SELECT Statements",
      "url": "https://docs.sqlalchemy.org/en/21/tutorial/data_select.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["select() builds every SELECT for Core and ORM", "where() can be called repeatedly; conditions are ANDed", "Session.execute returns Row objects; Session.scalars returns the first column (usually the entity)", "join() and join_from() accept an explicit ON clause; isouter renders LEFT OUTER JOIN", "group_by() and func.count() for aggregates; .desc() for descending order"]
    },
    {
      "title": "SQLAlchemy 2.1 Documentation: ORM-Enabled INSERT, UPDATE, and DELETE statements",
      "url": "https://docs.sqlalchemy.org/en/21/orm/queryguide/dml.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["update(Model).where(...).values(...) is executed with session.execute", "synchronize_session defaults to 'auto'"]
    },
    {
      "title": "SQLAlchemy 2.1 Documentation: ORM Quick Start",
      "url": "https://docs.sqlalchemy.org/en/21/orm/quickstart.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["select(User).where(...) with session.scalars(); session.scalars(stmt).one() for a single result; select(...).join(...)"]
    }
  ]
}
---
## 1. select() is SQL, written in Python

A `select()` is a statement object. Printing it shows the SQL it will send, so you can always check it against what you'd have written. The data for this lesson: users ali (1), sara (2), omid (3); chats general, backend and empty; five messages.

```python
with SessionLocal() as session:
    # 1. One object (or None) by a column
    stmt = select(User).where(User.username == "sara")
    print(stmt)
    print(session.scalars(stmt).one_or_none())

    # 2. Filter, order, limit: a user's latest 2 messages
    stmt = (select(Message.body)
            .where(Message.sender_id == 1)
            .order_by(Message.id.desc())
            .limit(2))
    print(session.scalars(stmt).all())

    # 3. Several columns -> Row objects
    for row in session.execute(select(User.id, User.username).order_by(User.username)):
        print(row.id, row.username)
```

```console
SELECT users.id, users.username, users.bio, users.created_at
FROM users
WHERE users.username = :username_1
User(id=2, username='sara')
['after lunch', 'lunch?']
1 ali
3 omid
2 sara
```

- `User.username == "sara"` doesn't compare anything in Python: it builds a SQL condition with a **bound parameter** (`:username_1`). Placeholders, as in DB.M04, for free.
- **`session.scalars(stmt)`** gives the first column of each row: whole objects for `select(User)`, plain values for `select(Message.body)`.
- **`session.execute(stmt)`** gives `Row` objects (named tuples) when you select several columns.
- How many results do you expect? **`.all()`** a list; **`.one()`** exactly one, otherwise it raises; **`.one_or_none()`** one or `None`, and raises if there are several. Prefer these over `.first()`, which silently ignores extra rows and can hide a duplicate.
- Calling `.where()` again ANDs another condition. A `Select` is immutable: each call returns a new statement, so you can build one step by step.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from sqlalchemy import create_engine, func, select\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Order(Base):\n    __tablename__ = 'orders'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    customer: Mapped[str]\n    total: Mapped[int]\n\nengine = create_engine('sqlite://')\nBase.metadata.create_all(engine)\nwith Session(engine) as s:\n    s.add_all([Order(customer='a', total=5), Order(customer='b', total=7), Order(customer='a', total=3)])\n    s.flush()\n    print(s.scalars(select(Order.total).where(Order.customer == 'a').order_by(Order.total)).all())",
  "answer": "[3, 5]",
  "explanation": "scalars() returns the single selected column as plain values, filtered to customer 'a' and sorted ascending." }
```

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "You look up a user by email, which should be unique. Which call do you want, and why?",
  "options": ["`.one_or_none()`: None when missing, and an error if a duplicate ever sneaks in", "`.first()`: it's the fastest", "`.all()[0]`", "`.one()`: it returns None when there's no row"], "answer": 0,
  "explanation": "one_or_none() matches the expectation 'zero or one' and fails loudly on two. first() hides duplicates; one() raises when the row is missing; all()[0] raises IndexError." }
```

## 2. JOINs and aggregates

```python
    # 4. JOIN: the titles of ali's chats
    stmt = (select(Chat.title)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .join(User, User.id == ChatMember.user_id)
            .where(User.username == "ali")
            .order_by(Chat.title))
    print(session.scalars(stmt).all())

    # 5. GROUP BY: messages per chat, inner join vs outer join
    inner = (select(Chat.title, func.count(Message.id))
             .join(Message, Message.chat_id == Chat.id)
             .group_by(Chat.id)
             .order_by(Chat.title))
    print("inner:", session.execute(inner).all())
    outer = (select(Chat.title, func.count(Message.id))
             .outerjoin(Message, Message.chat_id == Chat.id)
             .group_by(Chat.id)
             .order_by(Chat.title))
    print("outer:", session.execute(outer).all())
    print(outer)
```

```console
['backend', 'general']
inner: [('backend', 2), ('general', 3)]
outer: [('backend', 2), ('empty', 0), ('general', 3)]
SELECT chats.title, count(messages.id) AS count_1
FROM chats LEFT OUTER JOIN messages ON messages.chat_id = chats.id GROUP BY chats.id ORDER BY chats.title
```

The DB.M02 rules apply unchanged:

- An **inner** join drops a chat with no messages: "empty" vanishes from the counts.
- A **LEFT OUTER** join keeps it with NULLs on the message side, and `count(messages.id)` counts only non-NULL values, so it's 0. `count(*)` would count the one NULL-padded row and say 1.
- Write the ON clause explicitly (`ChatMember.chat_id == Chat.id`). SQLAlchemy can infer it from foreign keys, but explicit is easier to review.
- To sort by an aggregate with a tie-break, pass several keys: `.order_by(func.count(Message.id).desc(), Chat.title)`.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "Same Order model as in q1, same three orders. What does this print?",
  "code": "from sqlalchemy import create_engine, func, select\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Order(Base):\n    __tablename__ = 'orders'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    customer: Mapped[str]\n    total: Mapped[int]\n\nengine = create_engine('sqlite://')\nBase.metadata.create_all(engine)\nwith Session(engine) as s:\n    s.add_all([Order(customer='a', total=5), Order(customer='b', total=7), Order(customer='a', total=3)])\n    s.flush()\n    stmt = select(Order.customer, func.sum(Order.total)).group_by(Order.customer).order_by(func.sum(Order.total).desc())\n    print(s.execute(stmt).all())",
  "answer": "[('a', 8), ('b', 7)]",
  "explanation": "Grouped by customer, a's totals add up to 8 and b's to 7; sorted by the sum, highest first. execute() returns Row objects, which print like tuples." }
```

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "A dashboard should list every user with their number of chats, but users who aren't in any chat are missing. The query is `select(User.username, func.count(ChatMember.chat_id)).join(ChatMember, ChatMember.user_id == User.id).group_by(User.id)`. What's the fix?",
  "options": ["Use .outerjoin(ChatMember, ...) so users without memberships keep a row, counted as 0", "Use func.count('*') instead", "Add .distinct()", "Group by username instead of id"], "answer": 0,
  "explanation": "An inner join removes users with no matching membership rows. With an outer join they stay, and count(chat_id) counts the NULL as 0." }
```

## 3. Updates: through an object, or as one statement

Two ways to add a like, with every statement printed by an engine event hook:

```python
@event.listens_for(engine, "before_cursor_execute")
def log_sql(conn, cursor, statement, parameters, context, executemany):
    print("  SQL:", statement, parameters)


with SessionLocal.begin() as session:
    print("ORM attribute change:")
    msg = session.get(Message, 1)
    msg.likes += 1
    session.flush()

    print("UPDATE with a SQL expression:")
    result = session.execute(update(Message).where(Message.id == 1).values(likes=Message.likes + 1))
    print("rows matched:", result.rowcount)
```

```console
ORM attribute change:
  SQL: SELECT messages.id, messages.chat_id, messages.sender_id, messages.body, messages.likes
FROM messages
WHERE messages.id = ? (1,)
  SQL: UPDATE messages SET likes=? WHERE messages.id = ? (1, 1)
UPDATE with a SQL expression:
  SQL: UPDATE messages SET likes=(messages.likes + ?) WHERE messages.id = ? (1, 1)
rows matched: 1
```

The first version is a **lost update** waiting to happen: it reads 0, Python computes 1, and the UPDATE sends **the number 1**. If two requests do this at the same time, both read 0, both send 1, and one like is lost, with no error. (DB.M06 reproduces this for real.) The second sends `likes + 1` and lets the database do the arithmetic. Use the object style for ordinary edits (a new title), and `update().values(col=Model.col + 1)` for counters. `result.rowcount` tells you how many rows matched, so 0 means "no such message".

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "Which statement adds 1 to a chat's message_count without risking a lost update?",
  "options": ["session.execute(update(Chat).where(Chat.id == cid).values(message_count=Chat.message_count + 1))", "chat = session.get(Chat, cid); chat.message_count = chat.message_count + 1", "chat = session.get(Chat, cid); chat.message_count += 1; session.commit()", "session.execute(update(Chat).where(Chat.id == cid).values(message_count=chat.message_count + 1))"], "answer": 0,
  "explanation": "Only the first sends the arithmetic to the database. The others compute the new number in Python from a value read earlier; the last one even reads it from a Python object." }
```

## 4. Your turn

Four repository functions: a lookup, keyset pagination over a chat's history, member counts that include empty chats (with a tie-break, which you've missed before, so read the spec twice), and an atomic like. The last test listens to the engine the way section 3 does and checks the exact UPDATE you send.

```exercise
DB.M07.L03.E1
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Why does the chat history use 'messages with id < the last id I saw' (keyset pagination) instead of LIMIT 20 OFFSET 40?",
  "model": "With OFFSET, new messages arriving between requests shift every row, so the client sees duplicates or skips messages, and the database still has to walk past all the skipped rows. 'id < last_id ORDER BY id DESC LIMIT 20' always continues exactly where the client stopped, and with an index (chat_id, id) it's a cheap range search however deep you page.",
  "explanation": "Keyset pagination is stable under inserts and stays fast deep into the history." }
```
