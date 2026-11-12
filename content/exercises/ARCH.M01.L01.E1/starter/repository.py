"""Data access only: SQL in, plain values out. No FastAPI imports, no business rules."""
import sqlite3


class RegistrationRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_capacity(self, event_id: int) -> int | None:
        """The event's capacity, or None if there is no such event."""
        raise NotImplementedError

    def count_registrations(self, event_id: int) -> int:
        """How many registrations the event has."""
        raise NotImplementedError

    def add(self, event_id: int, email: str) -> bool:
        """Insert one registration. Return False instead if it already exists (the UNIQUE constraint fails)."""
        raise NotImplementedError
