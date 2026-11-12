```python
def snapshot(conn):
    """Everything leave_chat could touch, in a comparable form."""
    return (
        conn.execute("SELECT * FROM chat_members ORDER BY chat_id, user_id").fetchall(),
        conn.execute("SELECT * FROM messages ORDER BY id").fetchall(),
    )


def test_success_is_committed(tmp_path):
    path = tmp_path / "chat.db"
    conn = chatdb.make_file_db(path)
    membership.leave_chat(conn, 1, 2, NOW)
    assert conn.in_transaction is False
    other = sqlite3.connect(path)
    assert other.execute("SELECT 1 FROM chat_members WHERE chat_id = 1 AND user_id = 2").fetchone() is None
    assert other.execute("SELECT count(*) FROM messages WHERE body = 'left the chat'").fetchone() == (1,)


def test_non_member_raises_and_leaves_nothing(tmp_path):
    path = tmp_path / "chat.db"
    conn = chatdb.make_file_db(path)
    other = sqlite3.connect(path)
    before = snapshot(other)
    with pytest.raises(membership.NotAMember):
        membership.leave_chat(conn, 4, 1, NOW)  # ana isn't in chat 4
    assert snapshot(conn) == before, "this connection still sees uncommitted changes"
    assert conn.in_transaction is False, "the failed transaction was left open"
    assert snapshot(other) == before, "a half-done leave was committed"


def test_other_memberships_are_untouched():
    conn = chatdb.make_db()
    membership.leave_chat(conn, 1, 2, NOW)
    assert conn.execute("SELECT chat_id FROM chat_members WHERE user_id = 2 ORDER BY chat_id").fetchall() == [
        (2,), (3,),
    ]
    assert conn.execute("SELECT count(*) FROM chat_members WHERE chat_id = 1").fetchone() == (2,)
```

**Which test catches which bug**

| Bug | Caught by | Why |
|---|---|---|
| never commits | `test_success_is_committed` | Only a second connection can tell committed from pending. |
| commits the message first | `test_non_member_raises_and_leaves_nothing` | The other connection sees a 'left the chat' message from a non-member. |
| no rollback | `test_non_member_raises_and_leaves_nothing` | The other connection sees nothing (it was never committed), so a test that only checks `other` **misses this bug**. The same connection still sees the message, and `in_transaction` is True. |
| swallows the error | `test_non_member_raises_and_leaves_nothing` | `pytest.raises` fails: nothing was raised. |
| leaves every chat | `test_other_memberships_are_untouched` (and the non-member test, since ana is in other chats) | User 2 must stay in chats 2 and 3. |

**Why these tests work**

- **Observe each promise from where it can be broken.** "Committed" is a statement about *other* connections; "nothing written" is a statement about *every* connection, including the caller's, because a pending change is one stray `commit()` away from being permanent.
- **Compare whole snapshots, not one count.** `snapshot()` catches any change to the two tables, including ones you didn't think of.
- **Use the data's known facts.** ana not being in chat 4 is what makes the non-member case real; check the sample data instead of guessing ids.

**Alternatives**

- Parametrize the non-member test over several (chat, user) pairs, including a chat that doesn't exist (999). Note that then the INSERT itself fails with `IntegrityError` (foreign key), not `NotAMember`, which is worth deciding on purpose.
- A pytest fixture that returns `(conn, other)` would remove the repeated setup. This exercise avoids fixtures so test_meta.py can call your tests directly.
