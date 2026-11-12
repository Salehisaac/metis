"""Data access only: SQL in, plain values out. No FastAPI imports, no business rules."""
import sqlite3


class RegistrationRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_capacity(self, event_id: int) -> int | None:
        """The event's capacity, or None if there is no such event."""
        row = self.conn.execute("SELECT capacity FROM events WHERE id = ?", (event_id,)).fetchone()
        return None if row is None else row[0]

    def count_registrations(self, event_id: int) -> int:
        """How many registrations the event has."""
        return self.conn.execute("SELECT COUNT(*) FROM registrations WHERE event_id = ?", (event_id,)).fetchone()[0]

    def add(self, event_id: int, email: str) -> bool:
        """Insert one registration. Return False instead if it already exists (the UNIQUE constraint fails)."""
        try:
            self.conn.execute("INSERT INTO registrations (event_id, email) VALUES (?, ?)", (event_id, email))
        except sqlite3.IntegrityError:
            return False
        return True
