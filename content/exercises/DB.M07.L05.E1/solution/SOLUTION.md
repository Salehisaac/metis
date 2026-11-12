```python
def upgrade() -> None:
    # NOT NULL needs a value for existing rows: the server default gives every row 0 ...
    with op.batch_alter_table("chats") as batch_op:
        batch_op.add_column(sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"))
    # ... and the backfill replaces it with the real count.
    op.execute(
        "UPDATE chats SET member_count = "
        "(SELECT count(*) FROM chat_members WHERE chat_members.chat_id = chats.id)"
    )


def downgrade() -> None:
    with op.batch_alter_table("chats") as batch_op:
        batch_op.drop_column("member_count")
```

**The two bugs**

1. `ADD COLUMN ... NOT NULL` with no default works on an **empty** table (the first test passed with the starter!),
   but SQLite refuses it as soon as rows exist: `Cannot add a NOT NULL column with default value NULL`. Your dev
   database was empty; production isn't.
2. `downgrade()` was `pass`, so `alembic downgrade -1` moved the version back while leaving the column in place.
   The schema and the version table then disagree, and the next `upgrade` fails with a duplicate column.

**Why the fix works**

- `server_default="0"` puts `DEFAULT 0` in the table: existing rows get 0 at once, and so does any later INSERT that
  doesn't mention the column (old app code still running during a deploy, raw SQL scripts).
- The correlated `UPDATE ... = (SELECT count(*) ... WHERE chat_members.chat_id = chats.id)` then replaces 0 with
  the real count for every chat; chats without members keep 0. It's plain SQL because a migration must not import
  your current ORM models: they describe the *latest* schema, not the schema at revision 0002.
- `drop_column` inside `batch_alter_table` makes Alembic rebuild the table with "move and copy" (create a temp
  table, copy the rows, drop, rename), so other columns and all rows survive. The round-trip test proves the pair is
  really reversible.

**Alternative:** add the column nullable, backfill, then `alter_column(..., nullable=False)` (the three-step pattern
from the lesson). That works too, but without a server default `test_new_chats_start_at_zero` fails: inserts that
don't know the column would break.
