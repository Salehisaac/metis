---
{
  "id": "DB.M07.L01",
  "title": "Mapping tables to classes with typed Mapped[] columns",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["DB.M04", "PY.M07"],
  "objectives": [
    "Explain what the Engine, the declarative Base and a mapped class are, compared with database/sql and struct tags in Go",
    "Map a table with Mapped[] annotations and mapped_column(), predicting NOT NULL from the annotation",
    "Choose between a Python-side default and a server_default, and read the DDL SQLAlchemy emits",
    "Declare foreign keys, a composite primary key and table-level constraints in __table_args__"
  ],
  "why": "Every FastAPI codebase you'll join uses an ORM, and SQLAlchemy 2.x is the standard in Python. You already write the SQL by hand (DB.M01–M04), so you can check that the classes produce exactly the schema you'd have written, instead of trusting whatever an AI generated.",
  "applications": [
    "Defining the models of a FastAPI service",
    "Reading an existing codebase's models and knowing which columns are required",
    "The input to Alembic autogenerate (L05)"
  ],
  "exercises": ["DB.M07.L01.E1"],
  "sources": [
    {
      "title": "SQLAlchemy 2.1 Documentation: ORM Quick Start",
      "url": "https://docs.sqlalchemy.org/en/21/orm/quickstart.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["Mapped classes subclass a DeclarativeBase subclass", "Columns use Mapped[] annotations with mapped_column()", "Nullability derives from whether Optional[] (or equivalent) is used", "create_engine('sqlite://', echo=True) logs SQL; Base.metadata.create_all(engine) emits CREATE TABLE"]
    },
    {
      "title": "SQLAlchemy 2.1 Documentation: Table Configuration with Declarative",
      "url": "https://docs.sqlalchemy.org/en/21/orm/declarative_tables.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["mapped_column derives datatype and nullability from Mapped; Optional[] or | None means NULL, otherwise NOT NULL", "Explicit mapped_column parameters take precedence", "Default type map: int -> Integer, str -> String, datetime -> DateTime", "__table_args__ takes a tuple of positional Table arguments such as constraints"]
    }
  ]
}
---
## 1. What the ORM gives you (and what it doesn't)

In DB.M04 you wrote a repository with `sqlite3`: SQL strings, placeholders, and rows turned into objects by hand. An ORM (object-relational mapper) automates the last part, and builds the SQL from Python expressions. SQLAlchemy has two layers:

- **Core:** SQL as Python objects (`select(...)`, `insert(...)`), close to the SQL you know.
- **ORM:** classes mapped to tables, plus a `Session` that tracks objects and writes changes (L02).

The Go comparison: an `Engine` is like `*sql.DB`, a connection pool you create once per process. A mapped class is like a struct with `db:"..."` or gorm tags, except the column definitions are typed attributes.

What it doesn't do: think for you. It emits the SQL you'd write by hand, so everything from DB.M01–M04 (joins, transactions, placeholders) still applies, and so will the indexing and locking modules later in the course (DB.M05–M06). This module keeps showing you the emitted SQL so the ORM never becomes magic.

## 2. A mapped class

```python
from datetime import datetime

from sqlalchemy import ForeignKey, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    bio: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str]
    likes: Mapped[int] = mapped_column(default=0)


engine = create_engine("sqlite://", echo=True)
Base.metadata.create_all(engine)
```

`"sqlite://"` is an in-memory database. `echo=True` logs every SQL statement. `create_all` creates the tables that don't exist yet (on this machine, SQLAlchemy 2.1.6; log prefixes trimmed):

```console
BEGIN (implicit)
PRAGMA main.table_info("users")
...
CREATE TABLE users (
	id INTEGER NOT NULL,
	username VARCHAR(32) NOT NULL,
	bio VARCHAR,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (username)
)

CREATE TABLE messages (
	id INTEGER NOT NULL,
	sender_id INTEGER NOT NULL,
	body VARCHAR NOT NULL,
	likes INTEGER NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(sender_id) REFERENCES users (id)
)
COMMIT
```

Read it against the class:

- **The annotation picks the type**: `int` → `INTEGER`, `str` → `VARCHAR`, `datetime` → `DATETIME`.
- **The annotation picks NOT NULL**: `Mapped[str]` is `NOT NULL`; `Mapped[str | None]` (or `Optional[str]`) is nullable. That's the docs' rule, and it's the one people get wrong most.
- **`mapped_column()` adds the rest**: length, `unique`, `primary_key`, `ForeignKey`, defaults. Its explicit arguments win over the annotation.
- A single `int` primary key becomes SQLite's `INTEGER ... PRIMARY KEY (id)`, which SQLite treats as an alias for its internal row id, the key the table itself is sorted by.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from sqlalchemy import String\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Post(Base):\n    __tablename__ = 'posts'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    title: Mapped[str] = mapped_column(String(200))\n    subtitle: Mapped[str | None]\n    views: Mapped[int] = mapped_column(default=0)\n\nprint([c.name for c in Post.__table__.columns if c.nullable])",
  "answer": "['subtitle']",
  "explanation": "Only subtitle is annotated with | None. id is the primary key, title and views are plain str/int, so they're NOT NULL." }
```

## 3. default vs server_default

Look again at `likes INTEGER NOT NULL`: **no DEFAULT in the DDL**, even though the class says `default=0`. And `created_at` *does* have `DEFAULT CURRENT_TIMESTAMP`.

- `default=0` is a **Python-side** default: SQLAlchemy fills in 0 when *it* inserts a row without `likes`. A raw `INSERT` from a script, another service or a migration gets `NOT NULL constraint failed`.
- `server_default=func.now()` is part of the **table**: the database fills it in, whoever inserts.

Rule of thumb: if other code (or a migration backfill, L05) might insert rows, use `server_default`. For timestamps, let the database's clock decide.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "A cron job inserts messages with plain SQL `INSERT INTO messages (sender_id, body) VALUES (?, ?)`. The model says `likes: Mapped[int] = mapped_column(default=0)`. What happens?",
  "options": ["It fails: the column is NOT NULL and the table has no DEFAULT", "likes is set to 0", "likes is set to NULL", "SQLAlchemy intercepts the SQL and adds 0"], "answer": 0,
  "explanation": "default= lives in SQLAlchemy, not in the table, so raw SQL doesn't see it. server_default='0' would put DEFAULT 0 in the DDL." }
```

## 4. Foreign keys, composite keys and table-level constraints

Chat membership has a **composite primary key**: give both columns `primary_key=True`, in the order you want:

```python
class ChatMember(Base):
    __tablename__ = "chat_members"

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

```console
CREATE TABLE chat_members (
	chat_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	joined_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (chat_id, user_id),
	FOREIGN KEY(chat_id) REFERENCES chats (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
)
```

`ForeignKey("chats.id")` names the **table and column**, not the class. The primary key's index is sorted by `chat_id` first, so it helps lookups by chat, not by user alone (DB.M05 explains why).

Constraints and indexes over **several columns** belong to the table, so they go in `__table_args__`, a tuple of extra `Table` arguments. For example, an index that serves "a chat's messages in time order" (DB.M05 covers how to choose index columns):

```python
from sqlalchemy import Index

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_chat_created", "chat_id", "created_at"),)
    ...
```

Note the trailing comma: `(x,)` is a tuple, `(x)` is just `x`. Give constraints and indexes **explicit names**: Alembic (L05) needs a name to drop or change one later.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "`ForeignKey(\"User.id\")` is correct when the mapped class is called User and its table is \"users\".", "answer": false,
  "explanation": "ForeignKey takes table.column, so it must be ForeignKey(\"users.id\"). Class names are used by relationship() (L04), not by ForeignKey." }
```

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "Which mapping gives a required column `title VARCHAR(100) NOT NULL`?",
  "options": ["title: Mapped[str] = mapped_column(String(100))", "title: Mapped[str | None] = mapped_column(String(100))", "title: Mapped[Optional[str]] = mapped_column(String(100))", "title = String(100)"], "answer": 0,
  "explanation": "Mapped[str] means NOT NULL; String(100) sets the length. The | None and Optional variants are nullable, and a bare String(100) isn't a mapped column at all." }
```

**Common mistakes**

- `Mapped[str]` for a column that's really optional: every insert without it fails.
- `default=` where you meant `server_default=` (section 3).
- `unique=True` on one column when the rule is "unique per combination": that needs a multi-column `UniqueConstraint` in `__table_args__`.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column\n\nclass Base(DeclarativeBase):\n    pass\n\nclass Counter(Base):\n    __tablename__ = 'counters'\n    id: Mapped[int] = mapped_column(primary_key=True)\n    hits: Mapped[int] = mapped_column(default=0)\n    misses: Mapped[int] = mapped_column(server_default='0')\n\nprint(Counter.__table__.c.hits.server_default is None, Counter.__table__.c.misses.server_default is None)",
  "answer": "True False",
  "explanation": "hits only has a Python-side default, so the table has no DEFAULT for it. misses has a server_default, which becomes DEFAULT '0' in the DDL." }
```

## 5. Your turn

The exercise's `models.py` already maps `User` and `Message`. Add `Contact` (a composite primary key and a database-filled timestamp) and `Reaction` (a unique rule over three columns). The tests read the mapped tables and try real inserts, including the duplicates that must fail.

```exercise
DB.M07.L01.E1
```
