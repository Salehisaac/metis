---
{
  "id": "DB.M08.L01",
  "title": "Constraints that protect your data, and PostgreSQL in Docker",
  "difficulty": "intermediate",
  "minutes": 90,
  "prerequisites": ["DB.M07", "OPS.M01"],
  "objectives": [
    "Start PostgreSQL with the official Docker image (docker run or compose) and know which settings matter",
    "Enforce rules with NOT NULL, UNIQUE, CHECK and FOREIGN KEY (with ON DELETE actions), and name the constraints",
    "Predict the gotchas: CHECK passes on NULL, UNIQUE allows several NULLs, SQLite foreign keys are off by default, SQLite's flexible typing vs STRICT",
    "Declare the same constraints in SQLAlchemy and enable SQLite foreign keys on every connection"
  ],
  "why": "Application checks race (DB.M06: check-then-insert) and other writers skip them: scripts, migrations, a second service. A constraint is the only rule that holds for every write. PostgreSQL enforces types and foreign keys strictly, while SQLite is lenient by default, so knowing the differences keeps your SQLite tests honest about production.",
  "applications": [
    "Making invalid states impossible: negative balances, orphan rows, unknown statuses",
    "A local PostgreSQL for development and integration tests",
    "Turning duplicate-submission bugs into clean IntegrityErrors you can map to 409"
  ],
  "exercises": ["DB.M08.L01.E1"],
  "sources": [
    {
      "title": "Docker Official Image: postgres (docker-library docs)",
      "url": "https://github.com/docker-library/docs/blob/master/postgres/README.md",
      "version": "postgres image docs (PostgreSQL 18 era); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["docker run --name some-postgres -e POSTGRES_PASSWORD=... -d postgres", "POSTGRES_PASSWORD is the only required variable; POSTGRES_USER defaults to postgres, POSTGRES_DB to the user name", "The compose example uses image: postgres, restart: always, shm_size: 128mb", "From PostgreSQL 18 the image's VOLUME is /var/lib/postgresql (PGDATA is version specific)"]
    },
    {
      "title": "PostgreSQL 18 Documentation: 5.5 Constraints",
      "url": "https://www.postgresql.org/docs/current/ddl-constraints.html",
      "version": "PostgreSQL 18 (docs 18.7); not run on this machine",
      "verified": "2026-11-12",
      "claims": ["A CHECK constraint is satisfied if its expression is true or null", "Constraints can be named with CONSTRAINT name, which clarifies errors and lets you refer to them", "By default NULLs are not equal for UNIQUE; NULLS NOT DISTINCT changes that", "ON DELETE CASCADE deletes referencing rows; RESTRICT prevents deleting a referenced row", "Exclusion constraints exist"]
    },
    {
      "title": "SQLite Foreign Key Support",
      "url": "https://www.sqlite.org/foreignkeys.html",
      "version": "SQLite docs, page updated 2026-10-25; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["Foreign key constraints are disabled by default and must be enabled per connection with PRAGMA foreign_keys = ON", "ON DELETE CASCADE deletes child rows with the parent"]
    },
    {
      "title": "CREATE TABLE (SQLite)",
      "url": "https://www.sqlite.org/lang_createtable.html",
      "version": "SQLite docs, page updated 2025-04-30; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["A CHECK that evaluates to NULL is not a violation", "CHECK constraints are verified on write"]
    },
    {
      "title": "STRICT Tables",
      "url": "https://www.sqlite.org/stricttables.html",
      "version": "SQLite docs, page updated 2025-06-12; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["By default an INTEGER column stores text that can't be converted as text", "STRICT tables (since 3.37.0) reject values that can't be losslessly converted to the column type"]
    },
    {
      "title": "SQLAlchemy 2.1 Documentation: SQLite dialect",
      "url": "https://docs.sqlalchemy.org/en/21/dialects/sqlite.html",
      "version": "SQLAlchemy docs 2.1.8; verified locally with SQLAlchemy 2.1.6",
      "verified": "2026-11-12",
      "claims": ["PRAGMA foreign_keys = ON must be emitted on every connection, e.g. with a connect event listener"]
    }
  ]
}
---
## 1. PostgreSQL in Docker

In production your FastAPI service will most likely talk to PostgreSQL. Locally you run it in a container, with the compose skills from OPS.M01.

**Not run on this machine (Docker / PostgreSQL unavailable); behaviour per the cited docs.**

```console
$ docker run --name academy-pg -e POSTGRES_PASSWORD=devpassword -p 5432:5432 -d postgres:18
```

```yaml
# compose.yaml
services:
  db:
    image: postgres:18
    restart: always
    shm_size: 128mb
    environment:
      POSTGRES_PASSWORD: devpassword   # the only required variable
      POSTGRES_DB: messenger           # defaults to the user name, which defaults to "postgres"
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql     # the image's data volume from PostgreSQL 18 on
volumes:
  pgdata:
```

What matters:

- `POSTGRES_PASSWORD` is the only required variable. `POSTGRES_USER` defaults to `postgres`, and `POSTGRES_DB` defaults to the user name.
- A **named volume** keeps your data when the container is recreated. From PostgreSQL 18 the image's volume is `/var/lib/postgresql` (the data directory inside it is version specific); for 17 and below the docs say to mount `/var/lib/postgresql/data`.
- Pin the major version (`postgres:18`), as you'd pin a Python dependency.

Everything else in this module runs here on SQLite. Where PostgreSQL behaves differently, the lesson says so.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "You start `postgres:18` with compose but without a `volumes:` entry, add some data, then run `docker compose down` and `up` again. What's the likely result?",
  "options": ["The data is gone: it lived in the removed container, not in a named volume", "The data is kept, because Postgres writes to the host automatically", "The container refuses to start without a volume", "Only the schema is kept"], "answer": 0,
  "explanation": "Without a named volume, down removes the container and its data. Mount a named volume at the image's data volume path to keep it." }
```

## 2. Why the database should enforce rules

You could check "title isn't blank" or "the chat exists" in Python. But:

- **Races**: "check, then insert" has a gap (DB.M06). A unique constraint closes it: the second insert fails, whatever the timing.
- **Other writers**: scripts, migrations, backfills and other services don't run your Python checks.
- **Bugs**: the next refactor forgets a check. The constraint doesn't forget.

Keep friendly validation in the API (Pydantic gives nice error messages), *and* put the invariant in the schema. Here is one schema with all four kinds:

```python
conn = sqlite3.connect(":memory:")
conn.execute("PRAGMA foreign_keys = ON")       # SQLite: off by default, per connection
conn.executescript("""
CREATE TABLE users (
    id       INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email    TEXT UNIQUE                     -- optional, but unique when present
);
CREATE TABLE chats (
    id    INTEGER PRIMARY KEY,
    title TEXT NOT NULL CONSTRAINT chk_chats_title_not_blank CHECK (length(trim(title)) > 0)
);
CREATE TABLE messages (
    id        INTEGER PRIMARY KEY,
    chat_id   INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    sender_id INTEGER NOT NULL REFERENCES users(id),
    body      TEXT NOT NULL,
    likes     INTEGER NOT NULL DEFAULT 0 CHECK (likes >= 0)
);
""")
```

After inserting users 1 and 2, chat 1 and two messages, each statement is attempted (`attempt` prints ok or the error):

```console
refused: INSERT INTO chats (title) VALUES ('   ') -> CHECK constraint failed: chk_chats_title_not_blank
refused: UPDATE messages SET likes = likes - 1 WHERE id = 1 -> CHECK constraint failed: likes >= 0
refused: INSERT INTO messages (chat_id, sender_id, body) VALUES (99, 1, 'to nowhere') -> FOREIGN KEY constraint failed
ok:      INSERT INTO users (username, email) VALUES ('omid', NULL), ('lena', NULL)
refused: INSERT INTO users (username, email) VALUES ('x', 'a@b.c'), ('y', 'a@b.c') -> UNIQUE constraint failed: users.email
refused: DELETE FROM users WHERE id = 2 -> FOREIGN KEY constraint failed
ok:      DELETE FROM chats WHERE id = 1
messages left: 0
```

- **CHECK** expresses any rule about one row. Named (`CONSTRAINT chk_...`), the error tells you which rule broke, and a migration can find it later. The `likes >= 0` CHECK also catches a decrement bug from DB.M06's counters.
- **FOREIGN KEY**: no message for a chat that doesn't exist. **ON DELETE CASCADE** deletes a chat's messages with it. Without an action, deleting a referenced row is refused (user 2 still has a message).
- **UNIQUE** allowed two NULL emails but not two equal ones (section 3).

```quiz
{ "id": "q2", "type": "choice", "label": "Application",
  "prompt": "Two requests register the same username at the same moment. The handler checks `SELECT 1 FROM users WHERE username = ?` first, then inserts. What guarantees there will never be two users with that name?",
  "options": ["A UNIQUE constraint on username: the second INSERT fails with an IntegrityError", "The SELECT check, if it runs inside the handler", "Validating the username with Pydantic", "Adding an index without UNIQUE"], "answer": 0,
  "explanation": "Both SELECTs can see 'no such user' before either INSERT. Only the database's unique constraint is checked at write time, for every writer. Catch the IntegrityError and return 409." }
```

## 3. Four gotchas

**1. SQLite ignores foreign keys unless you switch them on, per connection:**

```console
0
orphan inserted: [(99,)]
```

(`PRAGMA foreign_keys` reads 0 on a new connection, and a message pointing at chat 99 is accepted.) PostgreSQL always enforces foreign keys. If your tests run on SQLite without the PRAGMA, they pass on data that PostgreSQL would reject.

**2. A CHECK passes when its expression is NULL.** Both docs (SQLite and PostgreSQL) say so. `CHECK (price > 0)` accepts `NULL`, because `NULL > 0` is NULL, not false. If NULL isn't allowed, add `NOT NULL` too.

**3. UNIQUE allows many NULLs** (seen above with the emails). That's usually what you want for optional values. PostgreSQL can treat NULLs as equal with `UNIQUE NULLS NOT DISTINCT` (not run here).

**4. SQLite's types are suggestions, unless the table is STRICT:**

```console
[(123, 'integer'), ('abc', 'text')]
STRICT: cannot store TEXT value in INTEGER column tight.n
NULL passed the CHECK: 1
```

An ordinary `INTEGER` column converted `'123'` to 123 but stored `'abc'` as text. A `STRICT` table (SQLite ≥ 3.37) refused it, which is what PostgreSQL does for a wrong type. The last line is gotcha 2: `INSERT ... VALUES (NULL)` into `price INTEGER CHECK (price > 0)` succeeded.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('CREATE TABLE items (qty INTEGER CHECK (qty >= 0))')\nfor value in (5, None, -1):\n    try:\n        conn.execute('INSERT INTO items VALUES (?)', (value,))\n        print('ok', value)\n    except sqlite3.IntegrityError:\n        print('refused', value)",
  "answer": "ok 5\nok None\nrefused -1",
  "explanation": "NULL >= 0 evaluates to NULL, and a CHECK only fails when its result is false. Add NOT NULL if a quantity is required." }
```

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "In SQLite, a column declared `REFERENCES chats(id)` rejects values that don't exist in chats as soon as the table is created.", "answer": false,
  "explanation": "Foreign keys are disabled by default in SQLite and must be enabled with PRAGMA foreign_keys = ON on each connection. PostgreSQL enforces them always." }
```

## 4. The same constraints in SQLAlchemy

`CheckConstraint` and `ForeignKey(..., ondelete=...)` produce the same DDL, and a `connect` event turns on SQLite foreign keys for **every** connection the engine opens (the recipe from the SQLAlchemy SQLite docs, simplified):

```python
class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(CheckConstraint("length(trim(title)) > 0", name="chk_chats_title_not_blank"))


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    body: Mapped[str]


engine = create_engine("sqlite://")


@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()
```

```console
foreign_keys = 1
Chat refused: CHECK constraint failed: chk_chats_title_not_blank
Message refused: FOREIGN KEY constraint failed
```

(The docs' full recipe also switches the driver's `autocommit` around the PRAGMA, which matters if you use `sqlite3`'s `autocommit=False` mode.) Multi-column CHECKs go in `__table_args__`, like the composite constraints in DB.M07.

PostgreSQL has more constraint types, for example **exclusion constraints** ("no two bookings for the same room may overlap"). They're PostgreSQL-only and not covered here.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nconn = sqlite3.connect(':memory:')\nconn.execute('CREATE TABLE a (n INTEGER)')\nconn.execute('CREATE TABLE b (n INTEGER) STRICT')\nconn.execute(\"INSERT INTO a VALUES ('seven')\")\ntry:\n    conn.execute(\"INSERT INTO b VALUES ('seven')\")\n    print('b accepted it')\nexcept sqlite3.IntegrityError:\n    print('b refused it')\nprint(conn.execute('SELECT typeof(n) FROM a').fetchone()[0])",
  "answer": "b refused it\ntext",
  "explanation": "The ordinary table keeps 'seven' as text in an INTEGER column. The STRICT table refuses a value that can't be converted, as PostgreSQL would." }
```

## 5. Your turn

The exercise's schema has the right columns and no rules. Add them from the comments, including a CHECK that spans two columns ("a group chat must have a title") and the right ON DELETE behaviour for each foreign key, and make `connect()` enable foreign keys. Remember gotcha 2 when you write each CHECK.

```exercise
DB.M08.L01.E1
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Your team's tests run on SQLite, production runs PostgreSQL. Name two differences from this lesson that could let a bug pass the tests, and how you'd close each gap.",
  "model": "1) Foreign keys: SQLite ignores them unless PRAGMA foreign_keys = ON runs on every connection, so orphan rows pass the tests; add the connect event listener in the test engine. 2) Types: SQLite stores a string in an INTEGER column, PostgreSQL rejects it; use STRICT tables, or validate types at the API. Also run a smaller suite against a real PostgreSQL (in Docker, in CI) for anything dialect-specific.",
  "explanation": "SQLite is lenient by default; make it strict where you rely on it, and test PostgreSQL-specific behaviour on PostgreSQL." }
```
