---
{
  "id": "WEB.M01.L01",
  "title": "Path operations: path and query parameters",
  "difficulty": "beginner",
  "minutes": 100,
  "prerequisites": ["PY.M07"],
  "objectives": [
    "Write a FastAPI path operation for a given method and path, and call it with TestClient",
    "Declare typed path parameters and predict the 422 body for a value that doesn't convert",
    "Order fixed paths (/users/me) before parameterised ones and explain why",
    "Declare optional, required, boolean and range-checked query parameters and predict which requests get 422"
  ],
  "why": "Every endpoint you write in FastAPI starts here: a decorator, a path and typed parameters. FastAPI converts and validates those parameters for you, so most of the parsing code you'd write by hand in a Go handler disappears. You only get that benefit if you can predict exactly which request reaches your function and which one is rejected first.",
  "applications": [
    "Read endpoints of a messaging API: GET /users/{id}, GET /chats/{id}/messages?limit=20",
    "Filters and pagination with defaults and limits",
    "Fixed sub-resources such as /users/me next to /users/{id}"
  ],
  "exercises": ["WEB.M01.L01.E1"],
  "sources": [
    {
      "title": "FastAPI Tutorial: First Steps",
      "url": "https://fastapi.tiangolo.com/tutorial/first-steps/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["A path operation is a path plus an HTTP method ('operation'); @app.get('/') makes the function below handle GET /", "Path operation functions can be def or async def", "You can return dict, list, str, int and Pydantic models; they are converted to JSON", "FastAPI doesn't enforce any specific meaning for each method", "Interactive docs at /docs, schema at /openapi.json"]
    },
    {
      "title": "FastAPI Tutorial: Path Parameters",
      "url": "https://fastapi.tiangolo.com/tutorial/path-params/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Path parameters are declared with Python type annotations; the function receives the converted value", "A value that doesn't convert produces an error body with type int_parsing and loc ['path', name]", "Path operations are evaluated in order, so /users/me must be declared before /users/{user_id}"]
    },
    {
      "title": "FastAPI Tutorial: Query Parameters",
      "url": "https://fastapi.tiangolo.com/tutorial/query-params/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Function parameters that aren't in the path are query parameters", "A default value makes a query parameter optional; None makes it optional with no value", "No default makes it required; missing gives an error of type missing with loc ['query', name]", "bool accepts 1, true, on, yes (any case) as True and 0, false, off, no as False; an unrecognised value gives 422"]
    },
    {
      "title": "FastAPI Tutorial: Path Parameters and Numeric Validations",
      "url": "https://fastapi.tiangolo.com/tutorial/path-params-numeric-validations/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Query and Path accept the number constraints gt, ge, lt, le", "Annotated is the preferred style"]
    },
    {
      "title": "FastAPI Tutorial: Testing",
      "url": "https://fastapi.tiangolo.com/tutorial/testing/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["TestClient is based on HTTPX and is used directly with pytest", "Test functions are normal def and client calls are not awaited", "Path and query parameters go in the URL; JSON bodies in json=, headers in headers="]
    },
    {
      "title": "Go standard library: net/http ServeMux",
      "url": "https://pkg.go.dev/net/http",
      "version": "pkg.go.dev current docs (Go comparison only; Go is not run in this lesson)",
      "verified": "2026-11-12",
      "claims": ["Patterns have the form [METHOD ][HOST]/[PATH], e.g. GET /items/{id}", "Request.PathValue returns the value of a named wildcard", "If two or more patterns match, the most specific pattern takes precedence; conflicting patterns panic at registration"]
    }
  ]
}
---
## 1. From a Go handler to a path operation

You already know the REST side: resources, methods, status codes. This module is about **writing it in FastAPI**, so the theory stays short and every example runs.

In Go, with the method-and-wildcard patterns of the current `net/http` `ServeMux`, a read endpoint looks like this:

```go
mux.HandleFunc("GET /users/{id}", func(w http.ResponseWriter, r *http.Request) {
    id, err := strconv.Atoi(r.PathValue("id"))
    if err != nil { http.Error(w, "bad id", http.StatusBadRequest); return }
    json.NewEncoder(w).Encode(findUser(id))
})
```

In go-zero you'd declare the route in the `.api` file and get a generated handler that parses into a request struct. FastAPI does the same job with a **decorator and type hints**. The decorator registers the route; the type hint `user_id: int` replaces the `strconv.Atoi` and the error branch:

```python
# users_api.py
from typing import Annotated

from fastapi import FastAPI, Query

app = FastAPI()

USERS = [
    {"id": 1, "username": "ali", "country": "IR", "active": True},
    {"id": 2, "username": "sara", "country": "DE", "active": False},
    {"id": 3, "username": "omid", "country": "IR", "active": True},
]


@app.get("/users/me")
def read_me():
    return {"id": 1, "username": "ali"}  # real authentication arrives in WEB.M06


@app.get("/users/{user_id}")
def read_user(user_id: int):
    for user in USERS:
        if user["id"] == user_id:
            return user
    return None  # wrong on purpose: lesson 2 turns this into a 404


@app.get("/users")
def list_users(
    country: str | None = None,
    active: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    found = [u for u in USERS
             if (country is None or u["country"] == country)
             and (active is None or u["active"] == active)]
    return found[:limit]
```

FastAPI calls one method + path pair a **path operation**, and the function under the decorator a *path operation function*. You return plain dicts and lists; FastAPI turns them into JSON. You can use `def` or `async def` (async comes in the AS course; `def` is fine for now).

It's a real HTTP server. Started with `uvicorn users_api:app --port 40423` and called with curl:

```console
$ curl -i http://127.0.0.1:40423/users/2
HTTP/1.1 200 OK
server: uvicorn
content-length: 56
content-type: application/json

{"id":2,"username":"sara","country":"DE","active":false}
```

While the server runs, `/docs` shows interactive documentation generated from your type hints. You won't need the server for exercises, though: **`TestClient`** sends requests straight to the app object, no port or network needed, and it's what pytest uses.

```python
# try_it.py
from fastapi.testclient import TestClient

from users_api import app

client = TestClient(app)
r = client.get("/users/2")
print(r.status_code, r.json())
```

```console
$ python try_it.py
200 {'id': 2, 'username': 'sara', 'country': 'DE', 'active': False}
```

(Importing `TestClient` prints a `StarletteDeprecationWarning` about httpx on stderr with the installed versions. It's harmless; ignore it.)

`r.json()` is the parsed body, so JSON `false` shows as Python `False`. Test functions are plain `def`; nothing is awaited.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "In `def read_user(user_id: int)` under `@app.get(\"/users/{user_id}\")`, what does the `: int` annotation do at runtime?",
  "options": ["Nothing; Python ignores type hints, so user_id is the string from the URL", "FastAPI converts the path segment to int and rejects the request if it can't", "It makes mypy check the route, but the value is still a string", "It makes the parameter optional"], "answer": 1,
  "explanation": "Plain Python ignores hints, but FastAPI reads them to parse and validate each parameter. That's the `strconv.Atoi` plus error branch from the Go version, done for you." }
```

## 2. Path parameters: converted, or rejected with 422

Same app, a few more requests. Each line was printed by `print(url, "->", r.status_code, r.json())` in a loop over URLs:

```console
/users/abc -> 422 {'detail': [{'type': 'int_parsing', 'loc': ['path', 'user_id'], 'msg': 'Input should be a valid integer, unable to parse string as an integer', 'input': 'abc'}]}
/users/99 -> 200 None
```

Two lessons here:

- **`abc` never reaches your function.** FastAPI rejects it first with **422** and a body whose `detail` is a *list* of problems. Each has a `type` (machine-readable), a `loc` (where: `["path", "user_id"]`), a `msg` (human-readable) and the `input` it got. Lesson 3 is about reading these bodies; module WEB.M02 is about changing their format.
- **`/users/99` returns 200 with `null`.** FastAPI only checks the *shape* of the input. Whether user 99 exists is your logic, and returning `None` is a bug every client will trip over. Lesson 2 fixes it with a 404.

Over real HTTP, uvicorn names 422 "Unprocessable Entity" in the status line (`HTTP/1.1 422 Unprocessable Entity`). RFC 9110, the current HTTP spec, calls it "Unprocessable Content". Same code.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\n@app.get(\"/chats/{chat_id}\")\ndef read_chat(chat_id: int):\n    return {\"chat_id\": chat_id, \"doubled\": chat_id * 2}\n\nc = TestClient(app)\nprint(c.get(\"/chats/21\").json())\nprint(c.get(\"/chats/twenty\").status_code)",
  "answer": "{'chat_id': 21, 'doubled': 42}\n422",
  "explanation": "\"21\" is converted to the int 21, so doubling gives 42 (not \"2121\"). \"twenty\" can't be converted, so FastAPI answers 422 before read_chat runs." }
```

## 3. Route order: fixed paths first

FastAPI tries path operations **in the order you declare them** and uses the first one whose path matches. A path pattern like `/users/{user_id}` matches *any* single segment, including `me`. The type check happens *after* the match, so it doesn't make FastAPI move on to the next route. If `/users/{user_id}` came first, `GET /users/me` would be matched to it, and `me` would fail the int conversion with 422.

That's why `read_me` is declared above `read_user` in the example:

```console
/users/me -> 200 {'id': 1, 'username': 'ali'}
```

Go's `ServeMux` is different: when two patterns match, "the most specific pattern takes precedence", and conflicting patterns panic at registration. In FastAPI, the order is your job.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "The routes are declared in this order. What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\n@app.get(\"/users/{username}\")\ndef profile(username: str):\n    return {\"profile\": username}\n\n@app.get(\"/users/me\")\ndef me():\n    return {\"me\": True}\n\nprint(TestClient(app).get(\"/users/me\").json())",
  "answer": "{'profile': 'me'}",
  "explanation": "The first matching route wins. `{username}` is a str, so \"me\" converts without error and profile() handles it. The /users/me route is never reached." }
```

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "If `@app.get(\"/users/{user_id}\")` with `user_id: int` is declared before `@app.get(\"/users/me\")`, then `GET /users/me` still reaches the /users/me route, because \"me\" isn't an int.",
  "answer": false,
  "explanation": "Matching is by path pattern and declaration order. /users/{user_id} matches first, then the int conversion fails and the client gets 422. FastAPI doesn't try the next route." }
```

## 4. Query parameters: defaults, optional, required, bool

**Any function parameter that isn't in the path is a query parameter.** Its default decides whether it's required:

| Declaration | Meaning |
|---|---|
| `country: str \| None = None` | optional; `None` when absent |
| `limit: int = 10` | optional; 10 when absent |
| `q: str` (no default) | **required**: absent → 422 with `type` `missing`, `loc` `["query", "q"]` |
| `active: bool \| None = None` | `1`, `true`, `on`, `yes` (any case) → `True`; `0`, `false`, `off`, `no` → `False`; anything else → 422 |
| `limit: Annotated[int, Query(ge=1, le=50)] = 10` | optional, but must be 1–50 |

`Query(...)` inside `Annotated` adds validation to a query parameter. `ge`/`le` mean ≥ and ≤; `gt`/`lt` are the strict versions. The FastAPI docs recommend this `Annotated` style.

The output for the example app:

```console
/users?country=IR&limit=1 -> 200 [{'id': 1, 'username': 'ali', 'country': 'IR', 'active': True}]
/users?active=no -> 200 [{'id': 2, 'username': 'sara', 'country': 'DE', 'active': False}]
/users?active=maybe -> 422 {'detail': [{'type': 'bool_parsing', 'loc': ['query', 'active'], 'msg': 'Input should be a valid boolean, unable to interpret input', 'input': 'maybe'}]}
/users?limit=0 -> 422 {'detail': [{'type': 'greater_than_equal', 'loc': ['query', 'limit'], 'msg': 'Input should be greater than or equal to 1', 'input': '0', 'ctx': {'ge': 1}}]}
```

**Common mistakes:**

- `active: bool = False` can't distinguish "not given" from "false". Use `bool | None = None` when "don't filter" is a real option, as `list_users` does.
- Checking `if not country:` when you meant `if country is None:`. An empty `?country=` gives `""`, which is falsy too.
- Forgetting a limit cap. Without `le=50`, `?limit=1000000` is a valid request.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\n@app.get(\"/notifications\")\ndef notifications(muted: bool = False):\n    return muted\n\nc = TestClient(app)\nfor url in [\"/notifications?muted=on\", \"/notifications?muted=0\", \"/notifications\"]:\n    print(c.get(url).json())",
  "answer": "True\nFalse\nFalse",
  "explanation": "\"on\" is one of the accepted true values, \"0\" is a false value, and with no parameter the default False is used." }
```

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "`@app.get(\"/search\")` with `def search(q: str, limit: int = 10)`. What does `GET /search?limit=5` return?",
  "options": ["200 with q set to \"\"", "200 with q set to None", "422, because q has no default and is therefore required", "404, because the route needs q to match"], "answer": 2,
  "explanation": "A query parameter without a default is required. FastAPI answers 422 with type `missing` and loc [\"query\", \"q\"]. Query parameters never affect route matching, so it's not a 404." }
```

```quiz
{ "id": "q7", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import FastAPI, Query\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\n@app.get(\"/contacts\")\ndef contacts(page_size: Annotated[int, Query(gt=0, lt=30)] = 10):\n    return {\"page_size\": page_size}\n\nc = TestClient(app)\nfor url in [\"/contacts?page_size=29\", \"/contacts?page_size=30\"]:\n    r = c.get(url)\n    body = r.json()\n    print(r.status_code, body[\"page_size\"] if r.status_code == 200 else body[\"detail\"][0][\"type\"])",
  "answer": "200 29\n422 less_than",
  "explanation": "`lt=30` is strict: 29 passes, 30 fails with the error type less_than. With `le=30`, 30 would pass." }
```

## 5. Your turn: a message list endpoint

The exercise is a real endpoint for the messaging API: list a chat's messages, newest first, with paging and a filter. The data is an in-memory list; the database comes in WEB.M05.

Before you code, read the edge cases in the exercise and write down which requests should get 422 and which should get an empty list. Then run the tests:

```console
$ .venv/bin/python tools/scaffold.py WEB.M01.L01.E1
$ cd workspace/WEB.M01.L01.E1 && ../../.venv/bin/pytest
```

```exercise
WEB.M01.L01.E1
```

```quiz
{ "id": "q8", "type": "explain", "label": "Application",
  "prompt": "A teammate wants `GET /chats/{chat_id}/messages` to take `limit` with no maximum, \"because the mobile app always sends 20\". What would you say?",
  "model": "Put a cap on it (for example le=100) anyway. The mobile app isn't the only possible client: any script or attacker can send limit=1000000 and make the server load and serialise everything. Validation at the boundary costs one annotation and gives a clear 422 instead of a slow or crashing request.",
  "explanation": "Validate at the trust boundary, not by trusting the known client." }
```
