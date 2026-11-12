```python
async def get_conn():
    conn = await aiosqlite.connect(DB_PATH)
    try:
        yield conn
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise
    finally:
        await conn.close()


@app.get("/notes/{note_id}")
async def get_note(note_id: int, conn: Conn):
    cur = await conn.execute("SELECT id, title, body FROM notes WHERE id = ?", (note_id,))
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="note not found")
    return {"id": row[0], "title": row[1], "body": row[2]}
```

**Why it works**

- **One connection per request.** FastAPI runs `get_conn` for each request, so concurrent requests never share a connection (or its transaction). That's the same rule SQLAlchemy's docs give for `AsyncSession`: one session per task.
- **Code after `yield` is the unit of work's end.** If the endpoint returns normally, execution continues after `yield` and commits. If the endpoint raises (including `HTTPException(422)` in the batch endpoint), FastAPI throws that exception into the generator at the `yield`: the `except` rolls back and re-raises, so FastAPI still produces the error response and logs real errors. The FastAPI docs insist on that re-raise.
- **`finally` closes the connection on every path**: success, error, and cancellation (a `CancelledError` is not an `Exception`, so it skips the rollback branch, but `finally` still runs, and closing discards the uncommitted transaction).
- **`scope="function"`** on the dependency makes the exit code, and so the commit, run *before* the response is sent. With the default request scope the client could get `201 Created` for a commit that then fails.
- **`get_note`** uses a `?` placeholder (never an f-string in SQL) and turns "no row" into a 404.

**Common mistakes**

- Committing in `finally`: a failed batch would then commit its first rows. Commit only on the success path.
- `except Exception: await conn.rollback()` without `raise`: the error is swallowed, and FastAPI can't log it.
- A module-level connection shared by all requests: concurrent requests then interleave inside one transaction.

**Alternative:** `async with aiosqlite.connect(DB_PATH) as conn:` around the `try/yield` closes the connection for you; the commit/rollback logic stays the same. With async SQLAlchemy (lesson section 5), `async with async_session.begin() as session: yield session` does all four steps: the session's transaction context manager commits on success, rolls back and re-raises on error, and closes. aiosqlite has no such helper, which is why you wrote the steps by hand here.
