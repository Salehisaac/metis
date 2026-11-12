```python
def get_tx():
    db = Transaction()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(x_user_id: Annotated[int | None, Header()] = None) -> dict:
    user = USERS.get(x_user_id) if x_user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="missing or unknown X-User-Id")
    return user


def get_member_chat(chat_id: int, user: Annotated[dict, Depends(get_current_user)]) -> dict:
    chat = CHATS.get(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="chat not found")
    if user["id"] not in chat["members"]:
        raise HTTPException(status_code=403, detail="not a member of this chat")
    return chat
```

**Why it works**

- **`get_tx` has the three parts of a request-scoped resource.** Setup before `yield`; `except Exception` rolls back and then **re-raises**, so the `HTTPException(422)` from the batch still becomes a 422 and the `RuntimeError` still reaches the test; `finally` closes on every path. It never commits: the routes commit before returning, so a commit failure would turn into an error response instead of a 201 for unsaved data.
- **`get_current_user` declares a header.** `Header()` makes `x_user_id` come from `X-User-Id`; the `int` type makes FastAPI answer 422 for `ali`. Missing and unknown ids both give 401: there's no valid identity either way.
- **`get_member_chat` depends on `get_current_user`.** It takes `chat_id` from the path like any endpoint parameter. Because it needs the user, authentication always happens first (a missing header is 401 even for an unknown chat), then 404, then 403. The routes also declare `CurrentUser`; the per-request cache resolves the user once.
- **Overrides reach the sub-dependency.** Replacing `get_current_user` in a test changes the user that `get_member_chat` sees too.

**Alternatives**

- Hide private chats with 404 instead of 403 (RFC 9110 allows it), so non-members can't probe which chat ids exist.
- In WEB.M06, only the body of `get_current_user` changes (token verification); every route and test that overrides it stays the same.
- With SQLAlchemy (WEB.M05), `get_tx` becomes `with Session(engine) as session: yield session`, plus the same rollback-and-re-raise.
