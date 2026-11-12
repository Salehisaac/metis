```python
class Contact(Base):
    __tablename__ = "contacts"

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    nickname: Mapped[str | None] = mapped_column(String(64))
    added_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Reaction(Base):
    __tablename__ = "reactions"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", "emoji", name="uq_reactions_message_user_emoji"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    emoji: Mapped[str] = mapped_column(String(16))
```

**Why it works**

- The annotation decides nullability: `Mapped[str]` is `NOT NULL`, `Mapped[str | None]` is nullable. `mapped_column()`
  adds what the annotation can't say: the length (`String(64)`), the foreign key, the primary key flag, the default.
- Two columns with `primary_key=True` make a **composite primary key**, in declaration order. That also makes
  "the same contact twice" impossible, without a separate unique constraint.
- `server_default=func.now()` puts `DEFAULT CURRENT_TIMESTAMP` in the DDL, so the **database** fills `added_at`,
  even for inserts that don't go through the ORM. A Python-side `default=` would only apply to SQLAlchemy inserts.
- A unique constraint over several columns belongs to the table, not to a column, so it goes in `__table_args__` (a
  tuple: note the trailing comma). Naming it matters later: Alembic can only drop or change a constraint it can
  find by name (L05).

**Common mistakes the tests catch:** `unique=True` on `emoji` alone (then nobody else could use that emoji anywhere),
a missing `String(16)` length, or `Mapped[str]` for nickname (that makes it required).
