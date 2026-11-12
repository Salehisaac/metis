---
{
  "id": "WEB.M03.L02",
  "title": "Request-scoped resources and the current user",
  "difficulty": "intermediate",
  "minutes": 110,
  "prerequisites": [
    "WEB.M03.L01",
    "PY.M07"
  ],
  "objectives": [
    "Write a yield dependency that sets up a per-request resource and always cleans it up, and predict the order of setup, handler and cleanup for a success, an HTTPException and an unexpected error",
    "Apply the rule for transactional resources: roll back on any exception, re-raise it, and always close",
    "Explain why a commit belongs in the handler (or service) before returning, not after the yield",
    "Write a current-user dependency that answers 401, and an authorisation dependency on top of it that answers 403",
    "Replace the current user in tests with dependency_overrides"
  ],
  "why": "Two dependencies appear in almost every FastAPI endpoint you'll write: the database session and the current user. Get the first wrong and you leak connections or half-commit a failed request; get the second wrong and users act on each other's data. Both are small functions, and both are easy to test once they're dependencies.",
  "applications": [
    "Database sessions per request (WEB.M05)",
    "Temporary files and outbound clients that must be released",
    "Authentication and authorisation checks (WEB.M06)"
  ],
  "exercises": [
    "WEB.M03.L02.E1"
  ],
  "sources": [
    {
      "title": "FastAPI Tutorial: Dependencies with yield",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": [
        "Use yield instead of return and write the extra steps after it; use yield one single time",
        "Code up to and including yield runs before the response is created; code after yield runs after the response",
        "Exceptions raised in the path operation, including HTTPException, are passed to dependencies with yield",
        "If you catch an exception in a yield dependency, re-raise it (or raise another HTTPException); otherwise the client still gets a 500 but the server has no log of the error",
        "Their example: db = DBSession(); try: yield db; finally: db.close()"
      ]
    },
    {
      "title": "FastAPI Tutorial: Header Parameters",
      "url": "https://fastapi.tiangolo.com/tutorial/header-params/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": [
        "Header parameters are declared with Annotated[..., Header()]; without Header() they'd be query parameters",
        "Underscores in the parameter name are converted to hyphens; headers are case-insensitive"
      ]
    },
    {
      "title": "FastAPI Tutorial: Dependencies in path operation decorators",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-in-path-operation-decorators/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": [
        "dependencies=[Depends(...)] in the decorator runs dependencies whose value isn't needed",
        "Such dependencies can raise exceptions like normal ones"
      ]
    },
    {
      "title": "FastAPI Advanced: Testing Dependencies with Overrides",
      "url": "https://fastapi.tiangolo.com/advanced/testing-dependencies/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": [
        "Override a dependency that calls an external auth provider with one that returns a mock user, only for tests",
        "Overrides work wherever the dependency is used"
      ]
    },
    {
      "title": "RFC 9110: HTTP Semantics (sections 15.5.2, 15.5.4)",
      "url": "https://www.rfc-editor.org/rfc/rfc9110.html",
      "version": "RFC 9110 (June 2022, STD 97)",
      "verified": "2026-11-12",
      "claims": [
        "401 Unauthorized: the request has not been applied because it lacks valid authentication credentials",
        "403 Forbidden: the server understood the request but refuses to fulfil it; the client SHOULD NOT repeat it with the same credentials",
        "A server that wishes to hide the existence of a forbidden resource MAY respond with 404"
      ]
    },
    {
      "title": "FastAPI Tutorial: Handling Errors",
      "url": "https://fastapi.tiangolo.com/tutorial/handling-errors/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": [
        "HTTPException accepts headers=, e.g. for some types of security"
      ]
    },
    {
      "title": "tempfile: Generate temporary files and directories",
      "url": "https://docs.python.org/3.12/library/tempfile.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "mkdtemp() creates a temporary directory and returns its absolute path",
        "The user of mkdtemp() is responsible for deleting the directory and its contents"
      ]
    }
  ]
}
---
## 1. FastAPI drives your generator

In PY.M07.L04 you drove a resource generator by hand: setup before `yield`, teardown after it, and `throw()` to deliver an error at the `yield`. FastAPI does exactly that around each request, for every dependency that uses `yield`:

1. It runs your function up to the `yield` and injects the yielded value.
2. It runs the endpoint.
3. If the endpoint raised, it raises that exception **at your `yield`**. Otherwise it resumes after it.

The resource here is a scratch directory for an attachment upload: created per request, deleted afterwards whatever happens. (`tempfile.mkdtemp()` creates the directory, and its docs say the caller is responsible for deleting it.)

```python
# attachments_api.py
import os
import shutil
import tempfile
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

events: list[str] = []
seen_dirs: list[str] = []


def get_scratch_dir():
    path = tempfile.mkdtemp(prefix="upload-")
    seen_dirs.append(path)
    events.append("mkdir")
    try:
        yield path
    finally:
        shutil.rmtree(path)
        events.append("cleanup")


app = FastAPI()


@app.post("/chats/{chat_id}/attachments", status_code=201)
def upload(chat_id: int, text: str, scratch: Annotated[str, Depends(get_scratch_dir)]):
    file_path = os.path.join(scratch, "upload.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    events.append("handler")
    if text == "crash":
        raise RuntimeError("thumbnail generator crashed")
    if os.path.getsize(file_path) > 10:
        raise HTTPException(status_code=413, detail="attachment too large")
    return {"chat_id": chat_id, "bytes": os.path.getsize(file_path)}
```

Three requests: a small file, a file that's too large, and one where the endpoint has a bug. The script printed the status, the body, `events`, and whether the directory still exists:

```console
201 {'chat_id': 4, 'bytes': 5} ['mkdir', 'handler', 'cleanup'] False
413 {'detail': 'attachment too large'} ['mkdir', 'handler', 'cleanup'] False
test sees RuntimeError('thumbnail generator crashed') ['mkdir', 'handler', 'cleanup'] False
```

- **`finally` runs on every path**: success, `HTTPException`, unexpected error. The directory is gone each time.
- **The exception passes through untouched.** `get_scratch_dir` has no `except`, so the `HTTPException` still becomes the 413, and the `RuntimeError` still reaches the test (the default `TestClient` re-raises it).
- **Exactly one `yield`**, as the docs require.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import Depends, FastAPI, HTTPException\nfrom fastapi.testclient import TestClient\n\nactive = []\nlog = []\n\ndef typing_indicator(chat_id: int):\n    active.append(chat_id)\n    try:\n        yield\n    finally:\n        active.remove(chat_id)\n        log.append(f\"stop {chat_id}\")\n\napp = FastAPI()\n\n@app.post(\"/chats/{chat_id}/drafts\", dependencies=[Depends(typing_indicator)])\ndef save_draft(chat_id: int, text: str):\n    log.append(f\"save {len(active)}\")\n    if not text.strip():\n        raise HTTPException(status_code=422, detail=\"empty draft\")\n    return {\"saved\": True}\n\nc = TestClient(app)\nprint(c.post(\"/chats/3/drafts?text=hi\").status_code, log, active)\nlog.clear()\nprint(c.post(\"/chats/3/drafts?text=%20\").status_code, log, active)",
  "answer": "200 ['save 1', 'stop 3'] []\n422 ['save 1', 'stop 3'] []",
  "explanation": "The dependency (in the decorator, because its value isn't needed) marks the chat as active, the handler sees one active chat, and finally removes it after the handler, on success and on the HTTPException alike. A dependency can take path parameters like chat_id too." }
```

## 2. Transactions: the stricter rule

A scratch directory only needs cleanup. A **database transaction** also has *pending writes*, and those must not survive a failed request. Picture a request that blocks three users: it adds two blocks to the transaction, then the third user turns out not to exist and the endpoint raises 404. If the first two writes were kept, the client would see an error while the data changed anyway.

So a transaction dependency follows a stricter rule than section 1:

1. create the transaction before `yield`, and yield it;
2. if **any** exception arrives at the `yield`, undo the pending writes (**roll back**) and then **re-raise the same exception**;
3. **always close** the transaction, whatever happened.

Step 2's re-raise is not optional. The docs: if you catch an exception in a dependency with `yield`, re-raise it (or raise a new `HTTPException`); swallow it and the client gets a 500 while the server has no record of why. You'll write this dependency yourself in the exercise; it's section 1's structure plus one more block.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "An endpoint has added two writes to the request's transaction and then raises `HTTPException(404)`. In which order should the transaction dependency react?",
  "options": ["Commit, then close, then let FastAPI send the 404", "Roll back, re-raise the HTTPException, and close the transaction in finally", "Roll back and return normally, so the client gets a clean response", "Close only; pending writes disappear on their own"], "answer": 1,
  "explanation": "Rolling back drops the two pending writes, re-raising lets FastAPI turn the exception into the 404, and finally closes on every path. Returning normally would swallow the 404; committing would keep half a request." }
```

## 3. Commit before you return

Why not commit *after* the `yield`, so endpoints don't have to? Because of when that code runs. The docs say the code after `yield` runs **after the response**. On the installed version, a dependency whose commit fails after the `yield`:

```python
def get_tx():
    yield "tx"
    order.append("after-yield")
    raise RuntimeError("commit failed")
```

```console
$ # TestClient(app, raise_server_exceptions=False).post("/x"), where /x answers 201
201 {"ok":true} ['handler', 'after-yield']
```

The client was told **201 Created** for data that was never saved. With the default `TestClient` the test does see the `RuntimeError`, but a real client doesn't. So the rule for this course:

- the **endpoint (or service) commits** before it returns, so a failed commit becomes an error response;
- the **dependency** only rolls back on errors and cleans up.

This is the pattern WEB.M05 builds on with real sessions.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "If a yield dependency's code after the yield raises (for example, a failed commit), the client receives a 500 instead of the endpoint's success response.",
  "answer": false,
  "explanation": "That code runs after the response is created, so the client already has the success status (201 in the run above). Commit inside the endpoint or service, before returning." }
```

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "A yield dependency catches exceptions to roll back: `except Exception: tx.rollback()` with no `raise` after it. An endpoint raises `HTTPException(404)`. What is the most likely result?",
  "options": ["The client gets the 404 as usual", "The client gets a 500 instead of the 404", "FastAPI retries the request", "The rollback is skipped"], "answer": 1,
  "explanation": "The dependency ate the exception, so the 404 is never produced. On the installed version the client gets 500, and the default TestClient raises FastAPIError (\"Response not awaited ... a dependency with yield has a block with a bare except, or a block with except Exception\"). The docs: re-raise what you catch." }
```

## 4. The current user: 401 vs 403

Authentication is a dependency too. This example reads a bearer token from the `Authorization` header and looks it up in a **fake token table**:

```python
# auth_api.py
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException

USERS = {1: {"id": 1, "username": "ali", "admin": True}, 2: {"id": 2, "username": "sara", "admin": False}}
TOKENS = {"tok-ali": 1, "tok-sara": 2}  # FAKE token store; WEB.M06 issues and verifies real tokens


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> dict:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or token not in TOKENS:
        raise HTTPException(status_code=401, detail="invalid or missing token", headers={"WWW-Authenticate": "Bearer"})
    return USERS[TOKENS[token]]


CurrentUser = Annotated[dict, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> None:
    if not user["admin"]:
        raise HTTPException(status_code=403, detail="admins only")


app = FastAPI()


@app.get("/me")
def me(user: CurrentUser):
    return {"username": user["username"]}


@app.get("/admin/stats", dependencies=[Depends(require_admin)])
def stats():
    return {"users": len(USERS)}
```

`GET /me` with no header, a wrong token and Sara's token, then `/admin/stats` as Sara and as Ali (status, body and the `WWW-Authenticate` header, as the script printed them):

```console
401 {'detail': 'invalid or missing token'} Bearer
401 {'detail': 'invalid or missing token'} Bearer
200 {'username': 'sara'} None
{'detail': 'admins only'}
{'users': 2}
```

- **`Header()` is required**, or `authorization` would be a query parameter. Header names are case-insensitive, and underscores in the parameter name become hyphens.
- **`partition(" ")`** splits `"Bearer tok-sara"` into scheme and token without crashing on a missing header (`""` gives an empty scheme). The scheme is compared case-insensitively, so `bearer tok-ali` works too.
- **`headers={"WWW-Authenticate": "Bearer"}`** tells the client which scheme to use; `HTTPException` takes `headers=` for cases like this.
- **`require_admin` is a sub-dependency** that declares the current user itself, so authentication always runs first. It sits in the decorator because the endpoint doesn't need its return value.
- **This is still fake**: a static token table. WEB.M06 replaces the body of `get_current_user` with real token verification, and no endpoint changes. That's the point of making it a dependency.

The two codes mean different things (RFC 9110):

- **401**: the request lacks valid authentication credentials.
- **403**: "I understood the request, and the answer is no." The RFC says the client SHOULD NOT repeat it with the same credentials.

The same structure handles resources: a dependency that loads a chat (404 if it doesn't exist) and checks membership (403) can declare the current user as its own parameter. **Order of checks:** authenticate first (401), then find the resource (404), then authorise (403). RFC 9110 allows a server that wants to hide a forbidden resource to answer 404 instead of 403, so outsiders can't even learn that a chat exists. Pick one and be consistent.

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "Sara is logged in (a valid identity) and tries to read a chat she isn't a member of. Which status fits RFC 9110 best (assuming you don't hide the chat's existence)?",
  "options": ["401 Unauthorized", "403 Forbidden", "404 Not Found", "409 Conflict"], "answer": 1,
  "explanation": "Her identity is known and valid, so it's not 401. The server understood the request and refuses it: 403. (404 is the alternative if you want to hide that the chat exists.)" }
```

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI, Header, HTTPException\nfrom fastapi.testclient import TestClient\n\ndef client_version(x_client_version: Annotated[str | None, Header()] = None) -> str:\n    if x_client_version is None:\n        raise HTTPException(status_code=400, detail=\"missing X-Client-Version\")\n    return x_client_version\n\napp = FastAPI()\n\n@app.get(\"/sync\")\ndef sync(version: Annotated[str, Depends(client_version)]):\n    return {\"version\": version}\n\nc = TestClient(app)\nprint(c.get(\"/sync\", headers={\"x-client-version\": \"5.2\"}).json())\nprint(c.get(\"/sync?x_client_version=5.2\").status_code)",
  "answer": "{'version': '5.2'}\n400",
  "explanation": "x_client_version is read from the X-Client-Version header; header names are case-insensitive, so x-client-version matches. A query parameter with the same name is ignored, because the parameter is declared with Header(), so the second request has no header: 400." }
```

## 5. Testing as any user

Tests shouldn't depend on how authentication works, or they all break when WEB.M06 replaces it. Override the dependency instead:

```python
app.dependency_overrides[get_current_user] = lambda: USERS[1]
print(c.get("/admin/stats").json())    # no Authorization header at all
app.dependency_overrides = {}
print(c.get("/admin/stats").status_code)
```

```console
{'users': 2}
401
```

The first request carried no token, and the override supplied Ali, an admin. Note that `require_admin` used the override too: overrides apply wherever the dependency appears in the tree. After the reset, the real `get_current_user` answers 401 again. This is exactly the docs' use case: replace a dependency that talks to an auth provider with one that returns a fixed user, only in tests. Keep at least one test that goes through the real dependency, so it stays covered.

```quiz
{ "id": "q7", "type": "truefalse",
  "prompt": "With `app.dependency_overrides[get_current_user] = lambda: USERS[2]`, a sub-dependency like `require_admin(user: CurrentUser)` still calls the real get_current_user, because only the endpoint's own parameters are overridden.",
  "answer": false,
  "explanation": "Overrides apply wherever the dependency appears in the tree, including inside sub-dependencies, as the /admin/stats run shows." }
```

## 6. Your turn: membership checks and a unit of work

The exercise is the messages endpoint of a group chat, and it uses neither a scratch directory nor bearer tokens. You transfer both patterns:

- a **transaction** dependency following section 2's rule (the `Transaction` class is given);
- a **current-user** dependency that reads a *different* header, an integer `X-User-Id`;
- a **membership check** built on the current user (404, then 403).

The finished routes use them. The tests check the status codes, that failed requests store nothing, that every transaction is closed, and that overrides work.

```exercise
WEB.M03.L02.E1
```
