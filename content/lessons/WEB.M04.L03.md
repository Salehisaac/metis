---
{
  "id": "WEB.M04.L03",
  "title": "Every path: parametrized status codes and error paths",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["WEB.M04.L02", "PY.M04"],
  "objectives": [
    "Turn an endpoint's contract into a table of requests and expected status codes covering normal, invalid, edge and error paths",
    "Write a parametrized API test with readable ids using pytest.param(..., id=...)",
    "Test both sides of every boundary (limits, lengths) instead of one value in the middle",
    "Test an error path by overriding a dependency with one that raises, and explain what raise_server_exceptions changes"
  ],
  "why": "The module outcome is 'normal, invalid, edge and error paths for every endpoint'. Writing a separate function per case is slow, so people skip cases. A parametrized table makes each extra case one line, and the table itself becomes a readable spec: a reviewer can see at a glance that limit=0 and limit=101 are covered. Error paths (a database or provider that is down) can't be produced on demand, so they need a fake that fails.",
  "applications": [
    "A status-code table per router in a real API",
    "Locking down boundary behaviour before refactoring validation",
    "Proving an outage becomes a clean 503 instead of a stack trace"
  ],
  "exercises": ["WEB.M04.L03.E1"],
  "sources": [
    {
      "title": "pytest: How to parametrize fixtures and test functions",
      "url": "https://docs.pytest.org/en/stable/how-to/parametrize.html",
      "version": "pytest docs (stable); installed pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": [
        "@pytest.mark.parametrize takes the argument names as a comma-separated string and a list of tuples; the test runs once per tuple",
        "Failures are reported with a generated id in brackets, e.g. test_eval[6*9-42]"
      ]
    },
    {
      "title": "pytest API reference: pytest.param",
      "url": "https://docs.pytest.org/en/stable/reference/reference.html",
      "version": "pytest docs (stable); installed pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": ["pytest.param(*values, id=..., marks=...) specifies one parameter set; id is the id attributed to that set"]
    },
    {
      "title": "Starlette: Test Client",
      "url": "https://starlette.dev/testclient/",
      "version": "Starlette docs (current); installed starlette 1.10.0",
      "verified": "2026-11-12",
      "claims": ["By default the TestClient raises any exception that occurs in the application; raise_server_exceptions=False lets you inspect the 500 response"]
    },
    {
      "title": "FastAPI Advanced: Testing Dependencies with Overrides",
      "url": "https://fastapi.tiangolo.com/advanced/testing-dependencies/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["Overrides can be set inside a test function, for only that test"]
    }
  ]
}
---
## 1. From contract to table

Before writing any test code, write the endpoint's contract as rows. For a chats API, with `ChatIn.title` from 1 to 50 characters and `GET /chats?limit=` from 1 to 20:

| Request | Kind | Expected |
|---|---|---|
| POST `{"title": "ops"}` | normal | 201 |
| POST 50-character title | edge (upper limit, valid) | 201 |
| POST 51-character title | invalid (just past the limit) | 422 |
| POST `{"title": ""}` | invalid (lower limit) | 422 |
| POST `{}` | invalid (missing field) | 422 |
| POST `{"title": 7}` | invalid (wrong type) | 422 |
| GET limit=1 and limit=20 | edge (valid) | 200 |
| GET limit=0 and limit=21 | invalid | 422 |

**Boundaries come in pairs.** An off-by-one bug (`le=21` instead of `le=20`) moves exactly one boundary by one step. A test at `limit=10` can't see it; only the pair 20/21 can. It's the same thinking as the slice bounds you practised in PY.M03, applied to an API.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A text field has `Field(min_length=3, max_length=10)`. Which lengths make the best set of test rows?",
  "options": ["2 (422), 3 (201), 10 (201), 11 (422)", "5 (201)", "0 (422) and 100 (422)", "3 (201) and 10 (201)"], "answer": 0,
  "explanation": "Test both sides of each limit: the last invalid value and the first valid one. 0 and 100 are invalid too, but far from the limits, so they don't catch min_length=2 or max_length=11." }
```

## 2. The table as code: `parametrize` with ids

Each row becomes one `pytest.param`. The test body is written once:

```python
import pytest

TITLE_CASES = [
    pytest.param({"title": "ops"}, 201, id="normal"),
    pytest.param({"title": "x" * 50}, 201, id="max-length"),
    pytest.param({"title": "x" * 51}, 422, id="too-long"),
    pytest.param({"title": ""}, 422, id="empty"),
    pytest.param({}, 422, id="missing"),
    pytest.param({"title": 7}, 422, id="not-a-string"),
]


@pytest.mark.parametrize("body, expected", TITLE_CASES)
def test_create_chat_status(client, body, expected):
    response = client.post("/chats", json=body)

    assert response.status_code == expected, response.text


@pytest.mark.parametrize("limit, expected", [(1, 200), (20, 200), (0, 422), (21, 422)])
def test_list_limit_boundaries(client, limit, expected):
    response = client.get("/chats", params={"limit": limit})

    assert response.status_code == expected
```

```console
$ pytest -v test_chats_table.py
test_chats_table.py::test_create_chat_status[normal] PASSED              [ 10%]
test_chats_table.py::test_create_chat_status[max-length] PASSED          [ 20%]
test_chats_table.py::test_create_chat_status[too-long] PASSED            [ 30%]
test_chats_table.py::test_create_chat_status[empty] PASSED               [ 40%]
test_chats_table.py::test_create_chat_status[missing] PASSED             [ 50%]
test_chats_table.py::test_create_chat_status[not-a-string] PASSED        [ 60%]
test_chats_table.py::test_list_limit_boundaries[1-200] PASSED            [ 70%]
test_chats_table.py::test_list_limit_boundaries[20-200] PASSED           [ 80%]
test_chats_table.py::test_list_limit_boundaries[0-422] PASSED            [ 90%]
test_chats_table.py::test_list_limit_boundaries[21-422] PASSED           [100%]
======================== 10 passed, 1 warning in 0.08s =========================
```

- **Every row is a separate test** with its own fixtures (a fresh `client` per row), so one failing row doesn't hide the others. In Go this is a table-driven test with `t.Run(tc.name, ...)`, and `id=` plays the role of `tc.name`.
- **Why `id=`?** For plain numbers pytest builds a good id (`1-200`). For dicts it can't, and you get `body0-201`, `body1-422`: useless in a CI log. `id="too-long"` tells you which rule broke.
- `params={"limit": limit}` builds the query string. You could also write `"/chats?limit=0"` in the URL.
- `response.text` in the assert message shows the error body when a row fails.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does `pytest --collect-only -q test_ids.py` print first? The file contains:\n`@pytest.mark.parametrize(\"body, expected\", [({\"title\": \"ops\"}, 201), ({}, 422)])` above `def test_x(body, expected): pass`.",
  "code": "# shell: pytest --collect-only -q test_ids.py   (first two lines)",
  "answer": "test_ids.py::test_x[body0-201]\ntest_ids.py::test_x[body1-422]",
  "explanation": "pytest can't turn a dict into a readable id, so it uses the argument name plus the index (body0, body1), then the int. pytest.param(..., id=\"ok\") replaces that with a name you choose." }
```

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "With a function-scoped `client` fixture, a POST in one parametrized row can change what the next row sees.", "answer": false,
  "explanation": "Each row is a separate test, and a function-scoped fixture is created again for every test. Each row gets a fresh app, so rows are independent and can run in any order." }
```

## 3. Error paths: make a dependency fail

"What if the database is down?" is a real path, and your endpoint should answer it with something better than a stack trace, usually 503. You can't take the database down on demand, but you can override the dependency that provides it with one that raises.

First, know what TestClient does with an exception **nobody handles**:

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\n@app.get(\"/chats\")\ndef list_chats():\n    raise ConnectionError(\"db down\")\n\ntry:\n    TestClient(app).get(\"/chats\")\nexcept ConnectionError as exc:\n    print(\"raised:\", exc)\nprint(TestClient(app, raise_server_exceptions=False).get(\"/chats\").status_code)",
  "answer": "raised: db down\n500",
  "explanation": "By default TestClient re-raises unhandled server exceptions inside your test, so you see the real traceback. With raise_server_exceptions=False you get what a real client gets: a bare 500." }
```

So an unhandled exception fails your test loudly, which is good. When the app is *supposed* to turn the exception into a response, register an exception handler and test the response:

```python
# search_app.py
class SearchDown(Exception):
    pass


class SearchBackend:
    def find(self, q: str) -> list[str]:
        return [f"message about {q}"]  # really: a call to the search cluster


def get_search_backend() -> SearchBackend:
    return SearchBackend()


def create_app() -> FastAPI:
    app = FastAPI()

    @app.exception_handler(SearchDown)
    def search_down(request: Request, exc: SearchDown):
        return JSONResponse(status_code=503, content={"detail": "search unavailable"})

    @app.get("/search")
    def search(q: str, backend: Annotated[SearchBackend, Depends(get_search_backend)]):
        return backend.find(q)

    return app
```

In the test, the failing backend comes from an override set inside the test. The `client` fixture (previous lesson) builds a fresh `create_app()` and clears the overrides in its teardown:

```python
# test_search.py
from search_app import SearchDown, get_search_backend


def test_search_outage_is_503(client):
    class BrokenSearch:
        def find(self, q):
            raise SearchDown()

    client.app.dependency_overrides[get_search_backend] = BrokenSearch

    response = client.get("/search", params={"q": "go"})

    assert response.status_code == 503
    assert response.json() == {"detail": "search unavailable"}
```

```console
$ pytest -q
1 passed, 1 warning in 0.03s
```

`client.app` is the app the TestClient wraps, so a test that only has the `client` fixture can still reach `dependency_overrides`. The override is the class itself: FastAPI calls it, which creates a `BrokenSearch` instance.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI, Request\nfrom fastapi.responses import JSONResponse\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\nclass SearchDown(Exception):\n    pass\n\n@app.exception_handler(SearchDown)\ndef search_down(request: Request, exc: SearchDown):\n    return JSONResponse(status_code=503, content={\"detail\": \"search unavailable\"})\n\n@app.get(\"/search\")\ndef search(q: str):\n    raise SearchDown()\n\nclient = TestClient(app)\nprint(client.get(\"/search\", params={\"q\": \"go\"}).status_code)\nprint(client.get(\"/search\").status_code)",
  "answer": "503\n422",
  "explanation": "With q, the handler runs and raises SearchDown, which the exception handler turns into 503. Without q, validation fails first and the handler never runs: 422. Order matters: validation, then your code." }
```

## 4. How much is enough?

- **Every endpoint gets all four kinds** (normal, invalid, edge, error), but not every combination. Two rows per boundary, one per required field, one per error branch in the code.
- **Status-code tables don't replace body assertions.** A table proves the API *accepts and rejects* the right requests. The normal path still needs a separate test that checks the body and the state change (lesson 1).
- **Read the code for branches.** Every `if ...: raise HTTPException(...)` is a row. Every `Query(ge=..., le=...)` and `Field(...)` is a pair of rows.
- **Limitation:** a table can only show the bugs your rows reach. The exercise uses mutation testing to show you which bugs your table missed; real projects can use a mutation-testing tool for the same job.

```quiz
{ "id": "q6", "type": "choice", "label": "Debugging",
  "prompt": "Your table for `DELETE /chats/{chat_id}/messages/{message_id}` has rows for an existing message (204) and a missing message id (404). A bug lets a user delete a message by its id even when it belongs to a different chat. Which row catches it?",
  "options": ["A message id that exists, sent to the URL of a chat it doesn't belong to → 404", "A second delete of the same message → 404", "A non-integer message id → 422", "A request without a body → 422"], "answer": 0,
  "explanation": "Only a row where the message exists, but under another chat, separates a correct check (chat_id AND message_id) from a buggy one (message_id only)." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "Your team's Go admin panel had a `POST /users/{id}/ban` endpoint. Write the rows of a status-code table for it (request, kind, expected status), assuming bans need a reason of 1 to 200 characters and the user must exist. Skip authorization for now; it's WEB.M06.",
  "model": "Normal: existing user, reason 'spam' → 200 (or 204). Edge: reason of 200 characters → 200; banning an already banned user → 200 or 409, whichever the spec says (decide it!). Invalid: reason missing → 422; empty reason → 422; 201 characters → 422; non-integer id → 422. Error: unknown user id → 404; the user store raising → 503.",
  "explanation": "Writing the rows first surfaces questions the spec never answered, such as banning twice." }
```

## 5. Your turn

Build the full status-code table for the messages API and kill seven mutants. Every row runs on a fresh app with one seeded message, so you can write delete rows too.

```exercise
WEB.M04.L03.E1
```
