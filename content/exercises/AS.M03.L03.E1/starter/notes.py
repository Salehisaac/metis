"""A notes API on SQLite through aiosqlite. Finish get_conn and get_note."""
from typing import Annotated

import aiosqlite
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

DB_PATH = "notes.db"  # the tests point this at a temporary file

SCHEMA = "CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL)"


async def init_db(path: str) -> None:
    """Create the schema. Correct, don't change."""
    async with aiosqlite.connect(path) as conn:
        await conn.execute(SCHEMA)
        await conn.commit()


async def get_conn():
    """Request-scoped connection: one per request, opened from DB_PATH.

    Commit if the request handler finished without an exception, roll back if it raised
    (and let the exception continue), and always close the connection.
    """
    conn = await aiosqlite.connect(DB_PATH)
    yield conn


# scope="function": the dependency's exit code (the commit) runs before the response is sent.
Conn = Annotated[aiosqlite.Connection, Depends(get_conn, scope="function")]

app = FastAPI()


class NoteIn(BaseModel):
    title: str
    body: str


@app.post("/notes", status_code=201)
async def create_note(note: NoteIn, conn: Conn):
    cur = await conn.execute("INSERT INTO notes (title, body) VALUES (?, ?)", (note.title, note.body))
    return {"id": cur.lastrowid, "title": note.title, "body": note.body}


@app.post("/notes/batch", status_code=201)
async def create_many(notes: list[NoteIn], conn: Conn):
    """All or nothing: a blank title anywhere means 422 and no note from the batch is saved."""
    ids = []
    for note in notes:
        if not note.title.strip():
            raise HTTPException(status_code=422, detail="blank title")
        cur = await conn.execute("INSERT INTO notes (title, body) VALUES (?, ?)", (note.title, note.body))
        ids.append(cur.lastrowid)
    return {"ids": ids}


@app.get("/notes/{note_id}")
async def get_note(note_id: int, conn: Conn):
    """{"id", "title", "body"} of the note, or 404 with detail "note not found"."""
    raise NotImplementedError
