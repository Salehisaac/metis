# Reference solution

The changed parts of `app.py`:

```python
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
```

**Why it works**

- **`add_task` defers the work.** FastAPI runs background tasks after the response is sent, so the client gets its 201 without waiting for SMTP. The direct-call test proves it: after `signup(...)` returns, nothing has been sent, and one task is queued.
- **Queue after the commit.** The task is added after the `with conn:` block succeeded. A duplicate email raises `IntegrityError` inside the block, which becomes a 409, and no task is ever queued. Queuing first would send a welcome email for a signup that failed.
- **The task handles its own failure.** By the time it runs, the response is gone, so an exception can't become a useful status code. Starlette's docs also say that when one task raises, the tasks after it don't run. So the task catches, logs with `log.exception` (message plus traceback) and returns.
- **Why `except Exception` is acceptable here, when ARCH.M02.L02 said to catch narrowly:** this is the outermost boundary of a unit of work that nobody else will see, the equivalent of a goroutine's top-level recover-and-log. Inside business code, narrow catches still apply.

**What this still doesn't give you:** if the process restarts between the response and the task, the email is lost, and nothing retries a failed send. The log line is your only record. If the email must arrive, record it in the database in the same transaction as the user and let a worker deliver it with retries. That's the outbox, next lesson.

**Alternative:** `asyncio.create_task(...)` inside an async endpoint also runs work concurrently, but FastAPI doesn't track it. You must keep a reference to the task yourself (the asyncio docs warn that unreferenced tasks can be garbage-collected), and errors go nowhere by default. BackgroundTasks is the supported in-process option.
