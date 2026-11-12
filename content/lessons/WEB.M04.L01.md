---
{
  "id": "WEB.M04.L01",
  "title": "TestClient tests: arrange, act, assert",
  "difficulty": "intermediate",
  "minutes": 60,
  "prerequisites": ["WEB.M03", "PY.M04"],
  "objectives": [
    "Send requests to a FastAPI app with TestClient (json=, headers=, query strings) and read status_code, json() and headers",
    "Structure every API test as Arrange / Act / Assert with exactly one Act step",
    "Choose asserts that would fail for a realistic wrong response, not just for a crash",
    "Name the four kinds of path every endpoint needs a test for: normal, invalid, edge and error"
  ],
  "why": "Your Go admin panel had 92 tests, and an AI wrote all of them. This module is where you write them yourself. An API test is the cheapest proof that an endpoint does what its contract says: TestClient runs the whole FastAPI stack (routing, validation, dependencies, serialisation) in your process, with no server and no network, in milliseconds.",
  "applications": [
    "A test per endpoint path before a pull request is merged",
    "Reproducing a bug report as a failing test before fixing it",
    "Checking status codes and error bodies that a frontend or mobile client relies on"
  ],
  "exercises": ["WEB.M04.L01.E1"],
  "sources": [
    {
      "title": "FastAPI Tutorial: Testing",
      "url": "https://fastapi.tiangolo.com/tutorial/testing/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": [
        "Create a TestClient by passing your FastAPI application to it; it comes from Starlette and is based on HTTPX",
        "Test functions are normal def, not async def, and client calls are normal calls without await",
        "Pass a JSON body with json=, headers with headers=, path and query parameters in the URL, form data with data=",
        "Use plain assert statements, standard pytest"
      ]
    },
    {
      "title": "Starlette: Test Client",
      "url": "https://starlette.dev/testclient/",
      "version": "Starlette docs (current); installed starlette 1.10.0",
      "verified": "2026-11-12",
      "claims": [
        "By default the TestClient raises any exception that occurs in the application; raise_server_exceptions=False returns the 500 response instead",
        "The default base_url is http://testserver"
      ]
    }
  ]
}
---
## 1. What TestClient is

In Go you test a handler with `httptest.NewRecorder()`: you build a request, call the handler directly and inspect the recorder. No port is opened. FastAPI's `TestClient` is the same idea with a friendlier API:

```python
from fastapi.testclient import TestClient

client = TestClient(app)          # app is your FastAPI() object
response = client.get("/chats/1")
```

- `TestClient(app)` doesn't start a server. Each call runs the whole app in your process: routing, Pydantic validation, `Depends`, exception handlers and serialisation. That's why it catches bugs a plain function call misses (a wrong `status_code=`, a missing validation rule).
- It has the same API as HTTPX (and Requests): `client.get/post/put/patch/delete(url, json=..., headers=..., params=...)`.
- **Test functions are plain `def`, even when the endpoint is `async def`.** The client calls aren't awaited. TestClient deals with the event loop for you.
- The response gives you `response.status_code` (an int), `response.json()` (the parsed body), `response.text` and `response.headers`.

On this machine every TestClient import prints a `StarletteDeprecationWarning` about httpx. It's harmless; ignore it.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\nfrom pydantic import BaseModel\n\napp = FastAPI()\n\nclass ChatIn(BaseModel):\n    title: str\n\n@app.post(\"/chats\", status_code=201)\ndef create_chat(body: ChatIn):\n    return {\"title\": body.title}\n\nclient = TestClient(app)\nprint(client.post(\"/chats\", json={\"title\": \"ops\"}).status_code)\nprint(client.post(\"/chats\").status_code)\nprint(client.get(\"/chats\").status_code)",
  "answer": "201\n422\n405",
  "explanation": "A valid body gets the declared 201. No body at all fails validation: 422. There's no GET route for /chats, only POST, so the router answers 405 Method Not Allowed. All three come from FastAPI itself, which is exactly what TestClient lets you check." }
```

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "To test an `async def` endpoint, the test function must also be `async def` and `await client.get(...)`.", "answer": false,
  "explanation": "With TestClient, tests are normal def functions and calls are normal calls. You only need async tests when the test itself must await something else, such as an async database function." }
```

## 2. Arrange, Act, Assert

Every good test has three parts, in this order:

1. **Arrange:** build the input and put the app in the state the test needs (create a chat first, for example).
2. **Act:** make **one** request: the one this test is about.
3. **Assert:** check the response, and the state change if there is one.

Here is a small chats API and its first two tests:

```python
# chats_api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()
chats: dict[int, dict] = {}


class ChatIn(BaseModel):
    title: str = Field(min_length=1, max_length=50)


@app.post("/chats", status_code=201)
def create_chat(body: ChatIn) -> dict:
    chat = {"id": len(chats) + 1, "title": body.title}
    chats[chat["id"]] = chat
    return chat


@app.get("/chats/{chat_id}")
def get_chat(chat_id: int) -> dict:
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="chat not found")
    return chats[chat_id]
```

```python
# test_chats.py
from fastapi.testclient import TestClient

from chats_api import app

client = TestClient(app)


def test_create_chat_returns_201_and_the_chat():
    # Arrange
    new_chat = {"title": "backend"}

    # Act
    response = client.post("/chats", json=new_chat)

    # Assert
    assert response.status_code == 201
    assert response.json() == {"id": 1, "title": "backend"}


def test_get_unknown_chat_is_404():
    response = client.get("/chats/42")

    assert response.status_code == 404
    assert response.json() == {"detail": "chat not found"}
```

```console
$ pytest -q
..                                                                       [100%]
2 passed, 1 warning in 0.14s
```

In short tests a blank line between the parts is enough, as in the second test. Comments help while you're learning.

**Why only one Act?** When a test with three requests fails, you first have to work out *which* request broke. Setup requests belong in Arrange. If you want to check a second behaviour, write a second test.

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "A test does: `client.post(\"/chats\", json={\"title\": \"a\"})`, then `r = client.get(\"/chats/1\")`, then `assert r.json()[\"title\"] == \"a\"`. Which part is the POST?",
  "options": ["Arrange: it sets up the state that the GET is tested against", "Act: every request is an Act", "Assert: it checks that creating works", "None: tests shouldn't send two requests"], "answer": 0,
  "explanation": "The test is about GET /chats/1, so the GET is the Act. The POST only creates the chat it needs, which makes it Arrange. If the POST itself fails, the test still fails, but the name tells you what was being tested." }
```

## 3. Assert what would catch a real bug

A test protects only what it asserts. Ask yourself: **which wrong response would still pass my asserts?**

- `assert response.status_code < 300` still passes if create returns 200 instead of 201. Assert the exact code.
- `assert "id" in response.json()` still passes if the id is wrong. When the value is predictable, assert the value.
- Asserting only the status lets a wrong body through. Asserting only the body lets a wrong status through. Assert both.
- When a value isn't predictable (a timestamp, a random token), assert that it exists and has the right type. In the next lesson you'll make it predictable with a fake clock.

Put the response body in the failure message, so a red test explains itself:

```python
assert response.status_code == 201, response.text
```

**A classic mistake: `data=` instead of `json=`.** `data=` sends form fields, not JSON:

```python
def test_create_chat_with_form_data():
    response = client.post("/chats", data={"title": "ops"})

    assert response.status_code == 201
```

```console
>       assert response.status_code == 201
E       assert 422 == 201
E        +  where 422 = <Response [422 Unprocessable Entity]>.status_code

test_wrong.py:11: AssertionError
```

The endpoint expects a JSON body, so FastAPI rejects the form data with 422. It's the same reading rule as in PY.M01: the left side is what the app did (422), the right side is what you expected (201).

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "Your create test has `assert response.status_code == 201`. Which bug does it NOT catch?",
  "options": ["The endpoint stores the chat with the title in lowercase", "The endpoint returns 200", "Validation rejects valid titles with 422", "The endpoint crashes with an exception"], "answer": 0,
  "explanation": "The status is still 201, so only an assert on the body (or on a follow-up GET) catches a wrong stored value. A crash would also fail the test, because TestClient re-raises server exceptions by default." }
```

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\nfrom pydantic import BaseModel\n\napp = FastAPI()\n\nclass ChatIn(BaseModel):\n    title: str\n\n@app.post(\"/chats\", status_code=201)\ndef create_chat(body: ChatIn):\n    return {\"title\": body.title}\n\nclient = TestClient(app)\nr = client.post(\"/chats\", json={\"name\": \"ops\"})\nprint(r.status_code, r.json()[\"detail\"][0][\"loc\"])",
  "answer": "422 ['body', 'title']",
  "explanation": "The JSON has no title field, so validation fails. Each error in detail has a loc: it's in the body, at the field title. Assert on loc in tests. The msg text belongs to Pydantic and can change between versions." }
```

## 4. Four kinds of path, for every endpoint

"I tested it" usually means "I tried the happy path once". Your Go assessment showed exactly that pattern: only the given example was checked. For each endpoint, list four kinds of path:

| Kind | Question | For `POST /chats` |
|---|---|---|
| **Normal** | Does a valid request do the right thing? | valid title → 201 and the chat |
| **Invalid** | Is bad input rejected with the right 4xx? | missing title, empty title, 51 characters → 422 |
| **Edge** | What happens at limits and with "nothing"? | exactly 50 characters → 201; a title of spaces → ? |
| **Error** | What if something it relies on is missing or failing? | `GET /chats/42` that doesn't exist → 404; storage down → 503 |

The question marks matter. `"   "` passes `min_length=1`, because it has three characters. If the spec says blank titles are invalid, the app needs a validator, and you need a test that proves it. Edge cases are where your tests find out what the spec really says.

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "`GET /chats/{chat_id}/messages?limit=N` accepts limit from 1 to 100. Which set of limit values tests the boundaries best?",
  "options": ["1, 100 (expect 200) and 0, 101 (expect 422)", "50 (expect 200)", "-5 and 1000 (expect 422)", "1 and 100 (expect 200)"], "answer": 0,
  "explanation": "Off-by-one bugs live right at the boundary: ge=0 instead of ge=1, or le=1000 instead of le=100. Test both sides of each boundary. -5 and 1000 are far from the boundary, so they miss these bugs." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "List the tests you would write for `DELETE /chats/{chat_id}`, which returns 204 and removes the chat. Name each test and mark its kind (normal, invalid, edge, error).",
  "model": "Normal: delete an existing chat → 204 with an empty body, and a follow-up GET returns 404 (the state changed). Error: delete a chat id that doesn't exist → 404. Invalid: a non-integer id (/chats/abc) → 422. Edge: delete the same chat twice → the second call is 404. Optionally: deleting one chat leaves the others (GET still 200).",
  "explanation": "A good delete test checks the state change with a follow-up request, not just the 204." }
```

## 5. Your turn

The exercise flips the usual setup: the app is correct, and **you write the tests**. A checker then runs your tests against six copies of the app, each with one realistic bug (this is called *mutation testing*). A copy "survives" when all your tests still pass, which means your tests didn't assert the thing that broke.

Write the tests from the docstrings and `app.py` first. Read `test_meta.py` only after your first run.

```exercise
WEB.M04.L01.E1
```
