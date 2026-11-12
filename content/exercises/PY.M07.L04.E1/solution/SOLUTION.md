```python
def get_session(make_session):
    session = make_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**Why it works: the three ways a framework can continue from the yield**

| Framework does | What happens at the `yield` | Path through the code | Events |
|---|---|---|---|
| `next(gen)` (request succeeded) | `yield` returns normally | commit, then `finally` | commit, close |
| `gen.throw(err)` (request failed) | `err` is raised at the `yield` | `except`: rollback, `raise`, then `finally` | rollback, close |
| `next(gen)` and commit fails | the commit raises | same `except`: rollback, `raise`, `finally` | commit, rollback, close |
| `gen.close()` (abandoned) | `GeneratorExit` is raised at the `yield` | not an `Exception`, so skips `except`; `finally` runs | close |

- **The commit is inside the `try`**, right after the `yield`. If it were in an `else:` clause (or after the whole `try`), a failing commit would skip the rollback.
- **`except Exception` + bare `raise`.** The rollback happens and the caller still sees the *same* exception object. Without the `raise`, the error would be swallowed: `contextmanager` would treat it as handled, and FastAPI's docs warn that swallowing it in a dependency leaves the server with no log of the error.
- **`GeneratorExit` derives from `BaseException`**, not `Exception`, so `close()` doesn't trigger a rollback here. Not committing is what matters on this path.
- **`make_session()` is before the `try`.** If it raises, there is no session, and `finally` must not try to close one (it would fail with `UnboundLocalError` and hide the real error).
- Because it's a generator, `get_session(factory)` creates nothing until the first `next()`.

**Alternatives**

- Class-based: `__enter__` creates the session, `__exit__(exc_type, ...)` commits if `exc_type is None`, otherwise rolls back, then closes and returns `False`. It's longer, and FastAPI's dependency docs use the generator form.
