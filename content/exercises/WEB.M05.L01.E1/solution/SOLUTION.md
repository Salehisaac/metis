The changed parts of `app.py`:

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def get_session(request: Request):
    with request.app.state.session_factory() as session:
        yield session


def create_app(engine: Engine) -> FastAPI:
    app = FastAPI()
    app.state.session_factory = sessionmaker(engine)

    @app.post("/users", status_code=201)
    def create_user(body: UserIn, session: SessionDep) -> UserOut:
        user = User(username=body.username)
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="username taken")
        return UserOut(id=user.id, username=user.username)
    # list_users unchanged
```

**Why the starter broke**

- **The poisoned session.** The duplicate INSERT failed during flush. SQLAlchemy rolled back the database transaction, but the *Session* stays in a "you must call rollback() first" state until someone does. The starter never did, and the session was shared, so every later request got `PendingRollbackError`. One bad request took down the whole app until a restart.
- **The held connection.** `GET /users` started a transaction (SQLAlchemy begins one automatically on the first query) and nothing ended it. The shared session kept the connection checked out forever. With a real pool of 5 + 10 connections, 15 such sessions would block the 16th request.

**Why the fix works**

- `sessionmaker(engine)` is a factory with fixed configuration, created once. Sessions are cheap; the engine and its pool are the expensive, shared part.
- `with factory() as session:` closes the session at the end of the block, also when the endpoint raised. Closing rolls back whatever wasn't committed and returns the connection to the pool. Each request starts clean, so a failure can't leak into the next request.
- `session.rollback()` in the `except` isn't strictly needed here, because closing the session rolls back anyway. It's there because it keeps the session usable if the endpoint did more work after the error, and it states the intent.

**Alternative:** a module-level `SessionLocal = sessionmaker(engine)` and `def get_session(): with SessionLocal() as session: yield session`, as in the FastAPI docs. It works the same way, but tests then have to replace `get_session` with `dependency_overrides`; passing the engine to `create_app` lets tests just build an app on a test engine.
