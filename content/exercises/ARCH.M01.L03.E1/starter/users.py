"""Given: the protocol, the real repository and the service. Don't change this file."""
import sqlite3
from typing import Protocol, runtime_checkable


class DuplicateEmail(Exception):
    pass


@runtime_checkable
class UserRepo(Protocol):
    def add(self, email: str, name: str) -> int: ...

    def get_by_email(self, email: str) -> dict | None: ...


class SqliteUserRepo:
    """The real implementation. Its behaviour IS the contract."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " email TEXT NOT NULL UNIQUE COLLATE NOCASE,"
            " name TEXT NOT NULL)"
        )

    def add(self, email: str, name: str) -> int:
        try:
            cur = self.conn.execute("INSERT INTO users (email, name) VALUES (?, ?)", (email, name))
        except sqlite3.IntegrityError:
            raise DuplicateEmail(email) from None
        return cur.lastrowid

    def get_by_email(self, email: str) -> dict | None:
        row = self.conn.execute("SELECT id, email, name FROM users WHERE email = ?", (email,)).fetchone()
        return None if row is None else {"id": row[0], "email": row[1], "name": row[2]}


def signup(repo: UserRepo, email: str, name: str) -> int:
    email = email.strip()
    if "@" not in email:
        raise ValueError("invalid email")
    return repo.add(email, name.strip())
