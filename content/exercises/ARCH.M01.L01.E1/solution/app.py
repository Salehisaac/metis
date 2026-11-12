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
