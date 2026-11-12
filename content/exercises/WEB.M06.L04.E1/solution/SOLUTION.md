The changed parts of `app.py`:

```python
def require_role(*roles: str):
    """Return a dependency that gives the current user if their role is in roles, else 403."""

    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user

    return dependency


def visible_chat(store: Store, chat_id: int, user: User) -> Chat:
    """The chat if user may see it. Otherwise 404, so outsiders can't tell it exists."""
    chat = store.chats.get(chat_id)
    if chat is None or (user.id not in chat.member_ids and user.role != "admin"):
        raise HTTPException(status_code=404, detail="chat not found")
    return chat


    @app.post("/admin/users/{user_id}/ban")
    def ban_user(user_id: int, actor: Annotated[User, Depends(require_role("moderator", "admin"))],
                 store: StoreDep) -> dict:
        target = store.users.get(user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="user not found")
        allowed = target.role == "user" if actor.role == "moderator" else target.id != actor.id
        if not allowed:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        target.banned = True
        return {"id": target.id, "banned": True}

    # list_messages: replace the chat lookup with   visible_chat(store, chat_id, user)
    # delete_message: visible_chat(...) first, then after the message lookup:
        if message.author_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Not enough permissions")
```

**Why it works**

- **Two layers.** `require_role` decides "may this kind of account call this endpoint at all?" before the endpoint body runs, and it's reusable: `Depends(require_role("admin"))` on any route. The object rules ("only role user", "not yourself", "only the author") need the target, so they live in the endpoint, after loading it. The OWASP Authorization Cheat Sheet's point: check access to the *specific object* on every request, not just the role.
- **Deny by default.** `user.role not in roles` rejects every role you didn't list, including a typo or a role added next year. The ban rule is written as "allowed when ...", so anything unexpected ends in 403.
- **404 vs 403.** Outsiders get the same 404 for "chat 2 exists but you're not in it" and "chat 99 doesn't exist", so chat ids can't be probed. A member who isn't the author already knows the message exists, so 403 is honest and more useful there.
- **One helper for visibility.** Both chat endpoints call `visible_chat`, so "who may see a chat" is defined once. Copy-pasted checks are where one endpoint ends up forgetting.
- **401 stays 401.** No token, or a banned account (rejected in `get_current_user`), never reaches the role check.

**The story behind it:** this is the shape of the admin-panel bug from your Go work, where every logged-in operator could ban. Authentication alone answers "is this a real operator?". It never answers "may this operator ban this account?".

**Alternative:** express permissions as data, for example a dict from role to allowed actions plus ownership rules, or a policy library. The OWASP cheat sheet prefers attribute- and relationship-based checks over pure role lists as systems grow. "Author or admin" and "member of the chat" are already relationship-based rules.
