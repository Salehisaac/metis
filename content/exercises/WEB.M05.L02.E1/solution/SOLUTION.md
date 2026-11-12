The changed parts of `app.py`:

```python
def get_session(request: Request):
    with request.app.state.session_factory() as session:
        yield session


    @app.post("/chats", status_code=201)
    def create_chat(body: ChatIn, session: SessionDep) -> ChatOut:
        try:
            chat = Chat(title=body.title)
            session.add(chat)
            session.flush()  # sends the INSERT, so chat.id is known; nothing is committed yet

            for user_id in body.member_ids:
                if session.get(User, user_id) is None:
                    raise HTTPException(status_code=404, detail=f"user {user_id} not found")
                session.add(Member(chat_id=chat.id, user_id=user_id))

            if body.first_message is not None:
                session.add(Message(chat_id=chat.id, sender_id=body.member_ids[0], text=body.first_message))

            session.commit()  # the only commit: all three writes, or none
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="chat title taken or duplicate member")

        return ChatOut(id=chat.id, title=chat.title, member_ids=body.member_ids)
```

**Why each starter bug happened**

- **Chat without members.** The early `commit()` made the chat permanent before the members were checked. When user 99 turned out not to exist, there was nothing left to roll back. This is the DB.M03 lesson in web form: a crash or error between two commits leaves the first one done.
- **500 on a duplicate title.** The `IntegrityError` from the early commit wasn't caught, so it became an unhandled exception.
- **201 for unsaved data.** The duplicate member was only detected by the commit in `get_session`, after `yield`. Since FastAPI 0.118 that code runs after the response has been sent, so the client had already received 201. With the default TestClient you'd see the IntegrityError raised in the test; a real client would just see 201.

**Why the fix works**

- `flush()` sends the pending INSERTs inside the current transaction. The database assigns `chat.id`, constraints are checked, but nothing is committed. A later exception plus `close()` (from the dependency) undoes it.
- The single `commit()` sits in the endpoint, so a failure there still happens *before* the response, and can become a 409.
- `rollback()` in the `except` puts the session back into a usable state before the HTTPException. The 404 path doesn't need it, because the `with` in `get_session` closes the session, which rolls back.

**Alternatives**

- `with session.begin():` around the writes commits on success and rolls back on any exception. It only works on a session that hasn't started a transaction yet (no earlier query in the same session), so it fits a service function that receives a fresh session.
- A dependency that opens `with factory.begin() as session: yield session` and is declared with `Depends(get_session, scope="function")` (FastAPI 0.121+). Its exit code runs before the response, so the commit failure becomes a 500 instead of a lie. You'd still catch IntegrityError yourself to answer 409.
