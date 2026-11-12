---
{
  "id": "DB.M07.L05",
  "title": "Alembic: autogenerate, upgrade, downgrade and reversible migrations",
  "difficulty": "intermediate",
  "minutes": 100,
  "prerequisites": ["DB.M07.L04"],
  "objectives": [
    "Set up Alembic for a SQLAlchemy project (init, sqlalchemy.url, target_metadata, render_as_batch)",
    "Generate a migration with --autogenerate and review it before running it",
    "Move a database with upgrade, downgrade, current and history, and preview SQL with --sql",
    "Write a migration that adds a NOT NULL column to a populated table, with a downgrade that really reverses it"
  ],
  "why": "In your Go job, schema changes shipped as migrations the AI wrote. This lesson is about being the person who can review one: what the tool generates, what it gets wrong, and the two bugs that bite most often in production, NOT NULL columns on tables that already have rows, and downgrades that don't undo anything. It's the module's second outcome: write reversible migrations.",
  "applications": [
    "Every schema change in a FastAPI + SQLAlchemy service",
    "Reviewing migration pull requests (generated or hand-written)",
    "Rolling back a bad deploy with alembic downgrade"
  ],
  "exercises": ["DB.M07.L05.E1"],
  "sources": [
    {
      "title": "Alembic Tutorial",
      "url": "https://alembic.sqlalchemy.org/en/latest/tutorial.html",
      "version": "Alembic docs 1.20.1; run locally with Alembic 1.20.1",
      "verified": "2026-11-12",
      "claims": ["alembic init creates alembic.ini, env.py, script.py.mako and versions/", "sqlalchemy.url in alembic.ini sets the database", "Each revision has revision and down_revision ids and upgrade()/downgrade() functions", "upgrade head, downgrade base, relative targets like -1 and +2, partial revision ids", "alembic current and alembic history show state"]
    },
    {
      "title": "Alembic: Auto Generating Migrations",
      "url": "https://alembic.sqlalchemy.org/en/latest/autogenerate.html",
      "version": "Alembic docs 1.20.1; run locally with Alembic 1.20.1",
      "verified": "2026-11-12",
      "claims": ["Set target_metadata = Base.metadata in env.py", "alembic revision --autogenerate -m '...' writes a candidate migration", "Autogenerate is not intended to be perfect; always review and correct its output", "Table and column renames are detected as add/drop pairs", "Anonymously named constraints can't be detected reliably; name them"]
    },
    {
      "title": "Alembic: Running \"Batch\" Migrations for SQLite and Other Databases",
      "url": "https://alembic.sqlalchemy.org/en/latest/batch.html",
      "version": "Alembic docs 1.20.1; run locally with Alembic 1.20.1",
      "verified": "2026-11-12",
      "claims": ["SQLite supports very little of ALTER", "Batch mode does move and copy: create the new table, copy data with INSERT ... SELECT, drop the old table, rename the new one", "Changes go inside op.batch_alter_table(); add_column alone uses a plain ALTER on SQLite", "render_as_batch=True in env.py makes autogenerate emit batch blocks"]
    }
  ]
}
---
## 1. Why migrations

`Base.metadata.create_all()` (L01) creates **missing** tables. It never changes an existing one. Here a model gained a `bio` column and `create_all` ran again on the same database:

```console
['id']
```

The table still has only `id`. Real schemas change every few weeks, and production has data you can't drop and recreate. A **migration tool** keeps the schema as a chain of versioned scripts:

- each **revision** has an id and the id of the revision before it (`down_revision`);
- `upgrade()` moves the schema forward; `downgrade()` moves it back;
- the database records which revision it's at, in a table called `alembic_version`.

Think of it as Git for the schema: revisions are commits, `upgrade head` is "check out the latest", `downgrade -1` is "go back one".

```quiz
{ "id": "q1", "type": "truefalse",
  "prompt": "After adding a column to a model, running `Base.metadata.create_all(engine)` adds the column to the existing table.", "answer": false,
  "explanation": "create_all only creates tables that don't exist yet. Changing an existing table is a migration's job." }
```

## 2. Setting up Alembic

Everything below ran for real in a scratch folder with Alembic 1.20.1 (long absolute paths shortened). The models are this module's `User`, `Chat` and `Message`.

```console
$ alembic init migrations
Creating directory .../migrations ...  done
Creating directory .../migrations/versions ...  done
Generating .../migrations/README ...  done
Generating .../migrations/env.py ...  done
Generating .../migrations/script.py.mako ...  done
Generating .../alembic.ini ...  done
Please edit configuration/connection/logging settings in .../alembic.ini before proceeding.
```

Three edits:

1. **`alembic.ini`**: `sqlalchemy.url = sqlite:///chat.db` (in a real service, read it from the environment in `env.py` instead of committing it).
2. **`migrations/env.py`**: tell autogenerate what the schema *should* be:

   ```python
   from models import Base

   target_metadata = Base.metadata
   ```

3. **Also in `env.py`**, in `run_migrations_online()`, add `render_as_batch=True` to `context.configure(...)`. SQLite supports very little `ALTER TABLE`; this makes generated migrations use Alembic's batch mode (section 5). It's harmless on other databases.

## 3. Autogenerate, then review

Autogenerate compares `target_metadata` with the live database and writes a **candidate** migration:

```console
$ alembic revision --autogenerate -m "create users chats messages"
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.autogenerate.compare.tables] Detected added table 'chats'
INFO  [alembic.autogenerate.compare.tables] Detected added table 'users'
INFO  [alembic.autogenerate.compare.tables] Detected added table 'messages'
Generating .../migrations/versions/d8cd3b5656a2_create_users_chats_messages.py ...  done
```

The generated file (excerpt):

```python
revision: str = 'd8cd3b5656a2'
down_revision: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('chats',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    ...


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('messages')
    op.drop_table('users')
    op.drop_table('chats')
```

"please adjust!" is meant literally. The Alembic docs say autogenerate "is not intended to be perfect" and that you must always review its output. What to look for:

- **Renames come out as drop + add.** Rename a column in the model and autogenerate writes "drop the old column, add a new one": every value in it is lost. Change it by hand to a rename.
- **Unnamed constraints** can't be tracked reliably. Name them (L01).
- **Data** is never handled: backfills are yours to write (section 6).

```quiz
{ "id": "q2", "type": "choice", "label": "Debugging",
  "prompt": "You renamed `Message.body` to `Message.text` in the model and ran autogenerate. The migration drops column body and adds column text. What happens if you run it on production as is?",
  "options": ["Every message's text is lost: the new column starts empty (or the migration fails if it's NOT NULL)", "Alembic notices the rename at runtime and copies the data", "Nothing: SQLite ignores column drops", "It renames the column, because drop+add is how renames work"], "answer": 0,
  "explanation": "The docs warn that renames are detected as an add/drop pair. Edit the migration to rename the column (batch_op.alter_column('body', new_column_name='text'))." }
```

## 4. Moving between revisions

After a second autogenerated revision (adding `messages.edited_at` and an index on `(chat_id, created_at)` for chat history):

```console
$ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade d8cd3b5656a2 -> cb72ff27b42f, add edited_at and chat index
$ alembic history
d8cd3b5656a2 -> cb72ff27b42f (head), add edited_at and chat index
<base> -> d8cd3b5656a2, create users chats messages
$ alembic current
cb72ff27b42f (head)
$ alembic downgrade -1
INFO  [alembic.runtime.migration] Running downgrade cb72ff27b42f -> d8cd3b5656a2, add edited_at and chat index
$ alembic current
d8cd3b5656a2
```

(The two `Context impl` / `non-transactional DDL` lines each command prints are trimmed.) `upgrade head`, `downgrade -1`, `downgrade base` and partial ids like `upgrade cb7` all work.

To review the exact SQL before touching a database, `--sql` prints it instead of running it:

```console
$ alembic upgrade d8cd3b5656a2:cb72ff27b42f --sql
-- Running upgrade d8cd3b5656a2 -> cb72ff27b42f

ALTER TABLE messages ADD COLUMN edited_at DATETIME;

CREATE INDEX ix_messages_chat_created ON messages (chat_id, created_at);

UPDATE alembic_version SET version_num='cb72ff27b42f' WHERE alembic_version.version_num = 'd8cd3b5656a2';
```

```quiz
{ "id": "q3", "type": "output",
  "prompt": "Using the history above, the database is at cb72ff27b42f (head). You run `alembic downgrade -1`. What does `alembic current` print next?",
  "code": "# alembic downgrade -1 && alembic current   (only the last line of output)",
  "answer": "d8cd3b5656a2",
  "explanation": "-1 moves back one revision, to cb72ff27b42f's down_revision. It's no longer head, so '(head)' isn't printed." }
```

## 5. SQLite and batch mode

Adding a column is a plain `ALTER TABLE` on SQLite. Most other changes aren't, so Alembic's batch mode does **move and copy**: create a new table, copy the rows, drop the old one, rename. Here is the SQL of a real downgrade that drops `users.display_name` (SQL logging on, reflection queries trimmed):

```console
CREATE TABLE _alembic_tmp_users (
	id INTEGER NOT NULL,
	username VARCHAR(32) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (username)
)

INSERT INTO _alembic_tmp_users (id, username, created_at) SELECT users.id, users.username, users.created_at
FROM users

DROP TABLE users
ALTER TABLE _alembic_tmp_users RENAME TO users
UPDATE alembic_version SET version_num='cb72ff27b42f' WHERE alembic_version.version_num = '990ace03356e'
COMMIT
```

Two consequences: batch needs a live database to read the current table, so `--sql` refuses it on SQLite ("batch mode with dialect sqlite requires a live database connection"); and on a big table it rewrites every row, so it takes time and SQLite's single write lock is held while it runs, so other writers wait (DB.M06).

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "Why does a SQLite migration that drops a column use `with op.batch_alter_table(\"users\") as batch_op:`?",
  "options": ["SQLite's ALTER TABLE is limited, so Alembic rebuilds the table: create a copy without the column, copy the rows, drop the old table, rename", "Batch mode runs the change faster by skipping transactions", "It's required for every migration on every database", "It lets Alembic drop the column without touching the data file"], "answer": 0,
  "explanation": "That's the move-and-copy procedure from the Alembic docs, visible in the SQL above. On other databases the same code emits ordinary ALTER statements." }
```

## 6. The production trap: NOT NULL on a table with rows

You add a required `display_name` to `users` with the obvious one-liner, `op.add_column("users", sa.Column("display_name", sa.String(64), nullable=False))`. The database already has users:

```console
$ alembic upgrade head
...
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) Cannot add a NOT NULL column with default value NULL
[SQL: ALTER TABLE users ADD COLUMN display_name VARCHAR(64) NOT NULL]
```

The existing rows would have no value. Worse, the same migration **succeeds on an empty table**, which is exactly what your dev database looks like:

```console
empty table: ok
with a row: Cannot add a NOT NULL column with default value NULL
[('x', 0)]
```

(That's three plain `sqlite3` statements: `ADD COLUMN a INTEGER NOT NULL` on an empty table, the same after inserting a row, then `ADD COLUMN b INTEGER NOT NULL DEFAULT 0`, which fills existing rows with 0.)

Two fixes:

- **A constant default makes sense** (a counter, a flag): add the column with `server_default=...`. Existing rows get it, and so do inserts from code that doesn't know the column yet.
- **The value is derived from other data**: expand, backfill, tighten:

```python
def upgrade() -> None:
    """Upgrade schema."""
    # 1. expand: add the column as nullable, so existing rows are allowed
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("display_name", sa.String(64), nullable=True))
    # 2. backfill: give every existing row a value
    op.execute("UPDATE users SET display_name = username WHERE display_name IS NULL")
    # 3. tighten: now no row is NULL, so NOT NULL can be enforced
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("display_name", existing_type=sa.String(64), nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("display_name")
```

```console
$ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade cb72ff27b42f -> 990ace03356e, add display_name
```

Afterwards the rows were `[(1, 'ali', 'ali'), (2, 'sara', 'sara')]` and `display_name` was NOT NULL.

Use **plain SQL (or `op.*`) for backfills, never your ORM models**: the models describe the *latest* schema, so an old migration that imports them breaks as soon as the models change again.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\nc = sqlite3.connect(':memory:')\nc.execute('CREATE TABLE t (id INTEGER PRIMARY KEY)')\nc.execute('INSERT INTO t VALUES (1)')\ntry:\n    c.execute('ALTER TABLE t ADD COLUMN n INTEGER NOT NULL')\n    print('added')\nexcept sqlite3.OperationalError as e:\n    print(e)",
  "answer": "Cannot add a NOT NULL column with default value NULL",
  "explanation": "The table has a row, and a NOT NULL column without a default would leave it NULL, so SQLite refuses. On an empty table the same statement succeeds, which is why this bug survives development." }
```

## 7. Reversible means tested

A downgrade that is `pass` (or wrong) is worse than none: `alembic downgrade` moves the version back while the schema stays changed, and the next upgrade crashes. Treat every migration as a pair and **test the round trip** on a database with data: upgrade, check the data, downgrade, check that the schema is back and the rows survived, upgrade again.

Some downgrades can't restore data (dropping a column throws its values away). That's acceptable if it's deliberate and written down in the migration's docstring; the schema must still go back exactly.

Your Go job's online-migration tooling addressed a related production problem: changing big tables without blocking traffic. The habits here still apply: review generated SQL, backfill explicitly, and never ship a migration you haven't run down and up again on real-looking data.

## 8. Your turn

Revision 0002 adds `chats.member_count`. It passed on its author's empty database, fails on a populated one, and its downgrade is `pass`. Fix it. The tests build a throwaway Alembic environment around your revision files and run real `upgrade` and `downgrade` commands.

```exercise
DB.M07.L05.E1
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "A teammate's PR adds `op.add_column('orders', sa.Column('currency', sa.String(3), nullable=False))` and `def downgrade(): pass`. Write your two review comments.",
  "model": "1) This fails on production because orders already has rows: a NOT NULL column needs a value. Add server_default='EUR' (if a default is correct), or add it nullable, backfill with an UPDATE, then alter it to NOT NULL. 2) downgrade must reverse the upgrade: drop the column (in batch_alter_table on SQLite). Please test upgrade -> downgrade -> upgrade on a database with rows.",
  "explanation": "The two classic migration bugs: NOT NULL on a populated table, and a downgrade that doesn't undo anything." }
```
