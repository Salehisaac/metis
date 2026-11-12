"""A working but 'fat' endpoint: HTTP, business rules and SQL all in one function.

Refactor it: SQL goes to repository.py, rules to service.py, and this file keeps only HTTP.
The HTTP behaviour must stay exactly the same (the API tests already pass: keep them green).
"""
import sqlite3
from typing import Annotated

import db
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
_conn = db.connect()


def get_conn():
    with _conn:  # one transaction per request: commit on success, roll back on error
        yield _conn


class RegistrationIn(BaseModel):
    email: str


@app.post("/events/{event_id}/registrations", status_code=201)
def register(event_id: int, body: RegistrationIn, conn: Annotated[sqlite3.Connection, Depends(get_conn)]):
    email = body.email.strip().lower()
    event = conn.execute("SELECT id, capacity FROM events WHERE id = ?", (event_id,)).fetchone()
    if event is None:
        raise HTTPException(404, "event not found")
    taken = conn.execute("SELECT COUNT(*) FROM registrations WHERE event_id = ?", (event_id,)).fetchone()[0]
    if taken >= event[1]:
        raise HTTPException(409, "event full")
    try:
        conn.execute("INSERT INTO registrations (event_id, email) VALUES (?, ?)", (event_id, email))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "already registered")
    return {"event_id": event_id, "email": email, "seats_left": event[1] - taken - 1}
