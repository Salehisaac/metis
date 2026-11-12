"""An in-memory UserRepo for fast service tests. It must behave exactly like SqliteUserRepo."""
from users import DuplicateEmail  # noqa: F401  (you'll need it)


class InMemoryUserRepo:
    def __init__(self):
        raise NotImplementedError

    def add(self, email: str, name: str) -> int:
        raise NotImplementedError

    def get_by_email(self, email: str) -> dict | None:
        raise NotImplementedError
