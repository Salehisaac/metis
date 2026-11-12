```python
def get_profile(conn, user_id):
    row = conn.execute("SELECT bio, version FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise LookupError(f"no user {user_id}")
    return row[0], row[1]


def update_bio(conn, user_id, new_bio, expected_version):
    cur = conn.execute(
        "UPDATE users SET bio = ?, version = version + 1 WHERE id = ? AND version = ?",
        (new_bio, user_id, expected_version),
    )
    conn.commit()
    if cur.rowcount == 1:
        return expected_version + 1
    get_profile(conn, user_id)  # raises LookupError if the user is gone
    raise ConflictError(f"user {user_id} changed since version {expected_version}")
```

**Why it works**

- The UPDATE is a **compare-and-set**: "write only if the version is still the one I read, and bump it in the same
  statement". The check and the write happen atomically inside one statement, so no other save can slip in between.
  (A SELECT to compare versions first, followed by the UPDATE, would reintroduce the L03 race.)
- `rowcount == 1` means you won. The new version is `expected_version + 1`, because the row only matched if its
  version *was* `expected_version`.
- `rowcount == 0` has two causes: the version moved on (conflict) or the row doesn't exist. Only on this rare
  failure path do you pay for a second query to tell them apart. Reusing `get_profile` gives you the LookupError.
- Saving the same text still bumps the version: the version tracks *saves*, not content, so every client that read
  the old version learns that someone saved after them.

**In an API:** map `ConflictError` to `409 Conflict` and let the client re-read and show the user what changed.
Don't silently retry a user's edit: the whole point is that a human chose the text based on what they saw.

**SQLAlchemy:** `__mapper_args__ = {"version_id_col": version}` makes the ORM add the same `AND version = ?` to its
UPDATEs and raise `StaleDataError` when 0 rows match.
