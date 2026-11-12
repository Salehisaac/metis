---
{ "id": "DB.M07.A", "module": "DB.M07", "title": "DB.M07 module assessment: SQLAlchemy and Alembic", "minutes": 20 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before WEB.M05.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "4 posts by 2 distinct authors, author loaded lazily. What does this print (names, number of SQL statements)?",
  "code": "from sqlalchemy import ForeignKey, create_engine, event, select\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Author(Base):\n    __tablename__ = 'authors'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    name: Mapped[str]\n\nclass Post(Base):\n    __tablename__ = 'posts'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    author_id: Mapped[int] = mapped_column(ForeignKey('authors.id'))\n    author: Mapped[Author] = relationship()\n\nengine = create_engine('sqlite://')\nBase.metadata.create_all(engine)\nwith Session(engine) as s, s.begin():\n    a, b = Author(name='a'), Author(name='b')\n    s.add_all([Post(author=a), Post(author=b), Post(author=a), Post(author=a)])\nsent = []\nevent.listen(engine, 'before_cursor_execute', lambda *args: sent.append(args[2]))\nwith Session(engine) as s:\n    names = [p.author.name for p in s.scalars(select(Post))]\nprint(names, len(sent))",
  "answer": "['a', 'b', 'a', 'a'] 3",
  "explanation": "1 SELECT for the posts, then one lazy load per distinct author not yet in the identity map: a and b. Later posts by a reuse the loaded object. joinedload(Post.author) would make it 1." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "from sqlalchemy import create_engine, select\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Note(Base):\n    __tablename__ = 'notes'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    text: Mapped[str]\n\nengine = create_engine('sqlite://')\nBase.metadata.create_all(engine)\nwith Session(engine) as s:\n    s.add(Note(text='draft'))\n    s.flush()\n    s.rollback()\n    print(s.scalars(select(Note)).all())",
  "answer": "[]",
  "explanation": "flush() sent the INSERT inside the transaction, but rollback() undid it. Only commit() makes a flush permanent." }
```

```quiz
{ "id": "a3", "type": "choice",
  "prompt": "`email: Mapped[str | None] = mapped_column(String(255), unique=True)`. Which DDL does this column produce?",
  "options": ["email VARCHAR(255), nullable, with UNIQUE (email)", "email VARCHAR(255) NOT NULL UNIQUE", "email TEXT NOT NULL", "email VARCHAR(255) DEFAULT NULL, no constraint"], "answer": 0,
  "explanation": "| None makes it nullable; String(255) sets the length; unique=True adds a UNIQUE constraint." }
```

```quiz
{ "id": "a4", "type": "choice", "label": "Debugging",
  "prompt": "A view counter does `post = session.get(Post, pid); post.views += 1; session.commit()`. Under load the counts are too low. What's the fix?",
  "options": ["session.execute(update(Post).where(Post.id == pid).values(views=Post.views + 1)), then commit", "Call session.flush() before commit", "Use session.begin() instead of commit()", "Load the post with joinedload"], "answer": 0,
  "explanation": "The ORM sends the computed number (views=11), a read-modify-write that loses concurrent updates. update().values(views=Post.views + 1) sends the arithmetic to the database." }
```

```quiz
{ "id": "a5", "type": "truefalse",
  "prompt": "If `alembic upgrade head` succeeds on your empty development database, a migration that adds a NOT NULL column without a default will also succeed in production.", "answer": false,
  "explanation": "SQLite (and other databases) refuse to add a NOT NULL column without a default to a table that has rows. Empty dev tables hide the problem; use a server_default, or add nullable, backfill, then tighten." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Describe how you'd structure database access for one FastAPI endpoint that creates an order with its line items, from session creation to commit, and how you'd make sure the response doesn't trigger lazy loads.",
  "model": "Create one sessionmaker at startup; per request open a session and run the use case in one `with SessionLocal.begin() as session:` block. Validate inputs, add the order and its items (flush if the order id is needed), and let the block commit, or roll back on any exception, including my own validation errors. Before the block ends, load everything the response needs: re-select the order with selectinload(Order.items) (and joinedload for many-to-one fields) or build the response DTO inside the block, so nothing lazy-loads after the session closes.",
  "explanation": "One session and one transaction per request; eager-load inside it; nothing shared between requests." }
```
