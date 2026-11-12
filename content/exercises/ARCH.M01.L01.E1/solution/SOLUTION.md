# Reference solution

`repository.py`

```python
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
```

`service.py`

```python
"""Business rules only. No FastAPI imports, no SQL."""
from repository import RegistrationRepo


class RegistrationError(Exception):
    """Base class for rule violations."""


class EventNotFound(RegistrationError):
    pass


class EventFull(RegistrationError):
    pass


class AlreadyRegistered(RegistrationError):
    pass


def register(repo: RegistrationRepo, event_id: int, email: str) -> int:
    """Register email for the event and return the seats left afterwards.

    Emails are compared after strip() and lower(). Raises EventNotFound, EventFull or AlreadyRegistered.
    """
    email = email.strip().lower()
    capacity = repo.get_capacity(event_id)
    if capacity is None:
        raise EventNotFound(event_id)
    taken = repo.count_registrations(event_id)
    if taken >= capacity:
        raise EventFull(event_id)
    if not repo.add(event_id, email):
        raise AlreadyRegistered(email)
    return capacity - taken - 1
```

`app.py`

```python
"""HTTP only: parse the request, call the service, map its errors to status codes."""
import sqlite3
from typing import Annotated

import db
import service
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from repository import RegistrationRepo

app = FastAPI()
_conn = db.connect()


def get_conn():
    with _conn:  # one transaction per request: commit on success, roll back on error
        yield _conn


class RegistrationIn(BaseModel):
    email: str


ERRORS = {
    service.EventNotFound: (404, "event not found"),
    service.EventFull: (409, "event full"),
    service.AlreadyRegistered: (409, "already registered"),
}


@app.post("/events/{event_id}/registrations", status_code=201)
def register(event_id: int, body: RegistrationIn, conn: Annotated[sqlite3.Connection, Depends(get_conn)]):
    try:
        seats_left = service.register(RegistrationRepo(conn), event_id, body.email)
    except service.RegistrationError as e:
        status, detail = ERRORS[type(e)]
        raise HTTPException(status, detail)
    return {"event_id": event_id, "email": body.email.strip().lower(), "seats_left": seats_left}
```

**Why it works**

- **Each layer answers one question.** The repository knows *how* registrations are stored, the service knows *whether* one is allowed, and the endpoint knows *what HTTP sees*. You can now test the rules with a plain function call (the `test_service_*` tests never start FastAPI).
- **Dependencies point down only.** `app` imports `service`, `service` imports `repository`. Nothing imports `app`. That's why `service.py` can't raise `HTTPException`: it would make the rules depend on the web framework, and a CLI or a queue worker calling `register` would get HTTP errors.
- **The repository hides the database.** `add` turns `sqlite3.IntegrityError` into `False`, so the service never imports `sqlite3`. Moving to SQLAlchemy later changes one file.
- **One error mapping.** The `ERRORS` dict plus one `except service.RegistrationError` means a new rule error can't silently become a 500 without you noticing: `ERRORS[type(e)]` raises `KeyError` for an unmapped error, which is loud in tests.

**Known limitation (on purpose, it's L02's topic):** `count_registrations` followed by `add` is a read-then-write. Two concurrent requests can both see 1 free seat and both insert. The fix belongs in one transaction with a conditional write, not in more Python checks.

**Alternatives**

- Map errors with FastAPI exception handlers (`@app.exception_handler(service.EventFull)`) instead of `try/except` in each endpoint. That's worth it once several endpoints share the same errors.
- Let the repository raise its own `DuplicateRegistration` exception instead of returning `False`. Both keep `sqlite3` out of the service; a boolean is enough for one caller.
