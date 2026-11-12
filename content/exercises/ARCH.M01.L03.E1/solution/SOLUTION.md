# Reference solution

```python
"""An in-memory UserRepo for fast service tests. It must behave exactly like SqliteUserRepo."""
from users import DuplicateEmail


class InMemoryUserRepo:
    def __init__(self):
        self._by_key: dict[str, dict] = {}  # lower-cased email -> stored user
        self._next_id = 1

    def add(self, email: str, name: str) -> int:
        key = email.lower()
        if key in self._by_key:
            raise DuplicateEmail(email)
        uid = self._next_id
        self._next_id += 1
        self._by_key[key] = {"id": uid, "email": email, "name": name}
        return uid

    def get_by_email(self, email: str) -> dict | None:
        user = self._by_key.get(email.lower())
        return None if user is None else dict(user)
```

**Why it works**

- **One dict keyed by `email.lower()`** reproduces `COLLATE NOCASE`: `ana@x.io` and `ANA@x.io` hit the same key, while the stored value keeps `Ana@X.io` as typed, just like the real table column.
- **Check before taking an id.** SQLite rejects the duplicate before `AUTOINCREMENT` hands out a new id, so the next good insert still gets 2. Taking the id first would make the fake drift from the real repository in a way only a careful test notices.
- **`dict(user)` returns a copy.** The real repository builds a new dict per query, so callers can mutate it freely. Returning the stored dict itself would let a test's mutation leak into the fake's state: the aliasing gap from PY.M02, in architecture clothes.
- **No `class InMemoryUserRepo(UserRepo)`.** It satisfies the Protocol structurally, like a Go type satisfying an interface. Subclassing the Protocol is allowed, but not needed.

**Why the contract test matters:** `test_contract_matches_the_real_repo` runs the same checks against SQLite. If someone later changes the real repository (say, drops `COLLATE NOCASE`), that test fails and tells you the fake and the contract need updating too. Without it, fakes quietly drift and service tests keep passing against behaviour production doesn't have.

**Alternatives**

- Skip the fake and run service tests against SQLite `:memory:`. For a SQLite-backed app that's often simpler and just as fast; fakes pay off when the real dependency is slow, remote or hard to set up (a payment API, PostgreSQL in CI without Docker).
- `unittest.mock.Mock(spec=...)` can stand in for the repository, but a mock only returns what you program, so it can't catch contract drift like a working fake can.
