"""Signups send a welcome email. Today the email is sent inline: slow, and a mail failure breaks the signup."""
import logging
import sqlite3
import time
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from pydantic import BaseModel

log = logging.getLogger("signup")
app = FastAPI()
_conn = sqlite3.connect(":memory:", check_same_thread=False)
_conn.execute("CREATE TABLE users (email TEXT PRIMARY KEY)")


class SmtpMailer:
    def send_welcome(self, email: str) -> None:
        time.sleep(2)  # a slow SMTP round trip; sometimes it raises instead


def get_conn() -> sqlite3.Connection:
    return _conn


def get_mailer() -> SmtpMailer:
    return SmtpMailer()


class SignupIn(BaseModel):
    email: str


def send_welcome_safely(mailer, email: str) -> None:
    """The background task: send the welcome email.

    If sending fails, log it on the 'signup' logger (mention the email) and return normally.
    """
    try:
        mailer.send_welcome(email)
    except Exception:
        # Nobody is waiting for this result any more, and an exception here would only
        # stop the tasks queued after it. Leave a trace someone can act on.
        log.exception("welcome email to %s failed", email)


@app.post("/signups", status_code=201)
def signup(
    body: SignupIn,
    background_tasks: BackgroundTasks,
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
    mailer: Annotated[SmtpMailer, Depends(get_mailer)],
):
    email = body.email.strip().lower()
    try:
        with conn:
            conn.execute("INSERT INTO users (email) VALUES (?)", (email,))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "email already registered")
    background_tasks.add_task(send_welcome_safely, mailer, email)  # runs after the response is sent
    return {"email": email}
