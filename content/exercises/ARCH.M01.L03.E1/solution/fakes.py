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
