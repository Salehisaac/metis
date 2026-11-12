```python
from typing import Annotated

from fastapi import FastAPI, Query

app = FastAPI()

MESSAGES = [...]  # unchanged


@app.get("/chats/{chat_id}/messages")
def list_messages(
    chat_id: int,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before: int | None = None,
    unread_only: bool = False,
):
    selected = [
        m for m in MESSAGES
        if m["chat_id"] == chat_id
        and (before is None or m["id"] < before)
        and not (unread_only and m["read"])
    ]
    newest_first = sorted(selected, key=lambda m: m["id"], reverse=True)
    return {"chat_id": chat_id, "messages": newest_first[:limit]}
```

**Why it works**

- **The signature is the validation.** `chat_id: int` comes from the path because the name is in `{chat_id}`. Everything else is a query parameter. The defaults make all three optional; `Query(ge=1, le=100)` rejects 0 and 101 with 422 before the function runs. `before: int | None = None` gives "no cursor" a value you can test with `is None` (a cursor of 0 would be falsy, so `if before:` would be a bug).
- **Order of operations matters.** Filter, then sort, then slice. Slicing before filtering would return fewer than `limit` unread messages even when more exist.
- **`sorted()` returns a new list.** `MESSAGES.sort()` would reorder the shared module-level list for every later request: the aliasing trap from PY.M02, now in a server.
- **Empty is not an error.** A chat with no messages gives `[]`. Whether chat 99 *exists* is a separate question; with a chats table you'd return 404 for an unknown chat (lesson 2).

**Alternatives**

- `before` is a *cursor*: the client passes the oldest id it has, and gets the next page. Offset paging (`?offset=40`) is simpler but skips or repeats items when new messages arrive between pages, which is constant in a chat.
- With a database (WEB.M05) the same logic becomes `WHERE chat_id = ? AND id < ? ORDER BY id DESC LIMIT ?`, so the database does the filtering instead of Python.
