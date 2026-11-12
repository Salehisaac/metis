---
{
  "id": "WEB.M01.L03",
  "title": "Error responses and debugging endpoints",
  "difficulty": "beginner",
  "minutes": 100,
  "prerequisites": ["WEB.M01.L01", "WEB.M01.L02"],
  "objectives": [
    "Name the two error body shapes FastAPI produces by default and which situations produce each",
    "Read a 422 body: use loc to find the source and field, and type rather than msg for program logic",
    "Return a structured error detail (code plus message) with HTTPException",
    "Test error paths by asserting on both status and body, and explain how TestClient treats unhandled exceptions",
    "Debug a broken endpoint from the status code and error body alone"
  ],
  "why": "Most of an API's contract is its failures: clients branch on them, and support tickets start from them. When a test fails, the status code and the error body usually tell you exactly which rule your endpoint broke, if you know how to read them. This lesson makes those bodies readable and sets up WEB.M02, where you'll give them one consistent format.",
  "applications": [
    "Client code that tells 'chat not found' from 'route not found' and 'invalid field'",
    "Fast diagnosis of a failing API test",
    "Machine-readable error codes for mobile clients"
  ],
  "exercises": ["WEB.M01.L03.E1"],
  "sources": [
    {
      "title": "FastAPI Tutorial: Handling Errors",
      "url": "https://fastapi.tiangolo.com/tutorial/handling-errors/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["HTTPException is raised, not returned, and ends the request", "detail can be any JSON-serialisable value, such as a dict or list, not only str", "HTTPException accepts headers=", "Invalid request data makes FastAPI raise RequestValidationError internally"]
    },
    {
      "title": "FastAPI Tutorial: Query Parameters",
      "url": "https://fastapi.tiangolo.com/tutorial/query-params/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Validation errors list items with type, loc, msg and input; a missing parameter has type missing", "An invalid bool value produces 422"]
    },
    {
      "title": "FastAPI Tutorial: Testing",
      "url": "https://fastapi.tiangolo.com/tutorial/testing/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Use TestClient like httpx: client.get/post, response.status_code, response.json()", "JSON bodies go in json=, headers in headers="]
    }
  ]
}
---
## 1. Two error shapes, out of the box

Everything in this lesson was run against small apps with `TestClient`. With no extra setup, a FastAPI app sends **two different error body shapes**:

| Situation | Status | Body |
|---|---|---|
| You raise `HTTPException(404, detail="chat not found")` | yours | `{"detail": "chat not found"}` |
| No route has this path | 404 | `{"detail": "Not Found"}` |
| Path exists, method doesn't | 405 | `{"detail": "Method Not Allowed"}` |
| Path, query or body fails validation | 422 | `{"detail": [ {"type": ..., "loc": [...], "msg": ..., "input": ...}, ... ]}` |

So `detail` is a **string** in some responses and a **list** in others. A client has to check which one it got before reading it. That's awkward, and WEB.M02 replaces it with one consistent format. First you need to read what's there.

## 2. Reading a 422

FastAPI validates the whole request and reports **every** problem at once, not just the first one:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel


class Invite(BaseModel):
    chat_id: int
    username: str


app = FastAPI()


@app.post("/invites", status_code=201)
def invite(body: Invite, notify: bool = True):
    return body


c = TestClient(app)
r = c.post("/invites?notify=perhaps", json={"chat_id": "seven"})
print(r.status_code)
for e in r.json()["detail"]:
    print(e["loc"], e["type"])
```

```console
422
['query', 'notify'] bool_parsing
['body', 'chat_id'] int_parsing
['body', 'username'] missing
```

How to read each item:

- **`loc`**: the first element is *where* the value came from (`path`, `query`, `body`, and later `header`). The rest is the field name, and for nested data the path inside it. `['query', 'title']` when you sent `title` in the JSON body means FastAPI looked in the query string: the parameter isn't declared as part of the body.
- **`type`**: a stable, machine-readable code (`missing`, `int_parsing`, `greater_than_equal`). Branch on this in code and in tests.
- **`msg`**: English for humans. It can change between library versions; don't compare against it.
- **`input`**: what was actually received. Very useful when debugging, but think about it before logging it: it may contain a password.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\nfrom pydantic import BaseModel\n\nclass Poll(BaseModel):\n    question: str\n    options: list[str]\n\napp = FastAPI()\n\n@app.post(\"/chats/{chat_id}/polls\")\ndef create_poll(chat_id: int, body: Poll):\n    return body\n\nr = TestClient(app).post(\"/chats/x/polls\", json={\"options\": \"yes\"})\nprint([(e[\"loc\"][0], e[\"loc\"][-1], e[\"type\"]) for e in r.json()[\"detail\"]])",
  "answer": "[('path', 'chat_id', 'int_parsing'), ('body', 'question', 'missing'), ('body', 'options', 'list_type')]",
  "explanation": "All three problems are reported in one response: the path id isn't an int, question is missing, and options is a string instead of a list. loc[0] says where each one came from." }
```

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "Your mobile client wants to highlight the right form field when the API answers 422. Which part of each error item should it use?",
  "options": ["`msg`, matched against known English sentences", "`loc` for the field and `type` for the kind of problem", "`input`, compared with what the user typed", "Only the status code; the body is for humans"], "answer": 1,
  "explanation": "loc names the source and field; type is the stable machine code. msg is human text that can change between versions." }
```

## 3. Structured error details

`detail` doesn't have to be a string. FastAPI accepts any JSON-serialisable value, so you can send a code the client can branch on, next to a message a person can read:

```python
@app.get("/blocked/{username}")
def blocked(username: str):
    raise HTTPException(status_code=403, detail={"code": "blocked", "message": f"{username} blocked you"})
```

```console
{'detail': {'code': 'blocked', 'message': 'sara blocked you'}}
```

`HTTPException` also takes `headers=`, for the rare error that needs one (authentication challenges in WEB.M06).

**Unknown route vs unknown resource.** A typo in the path (`GET /chatz/1`) gives FastAPI's own `{"detail": "Not Found"}`. A missing chat gives your 404. The status is the same, so a specific detail (or a code) is the only way the client, and you while debugging, can tell them apart.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI, HTTPException\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\n@app.post(\"/chats/{chat_id}/join\")\ndef join(chat_id: int):\n    raise HTTPException(status_code=409, detail={\"code\": \"already_member\", \"chat_id\": chat_id})\n\nc = TestClient(app)\nr = c.post(\"/chats/4/join\")\nprint(r.status_code, r.json()[\"detail\"][\"code\"])\nprint(c.post(\"/chat/4/join\").json())",
  "answer": "409 already_member\n{'detail': 'Not Found'}",
  "explanation": "The first request reaches join() and gets your structured detail. The second has a typo (/chat/ instead of /chats/), matches no route, and gets FastAPI's default 404 body with a plain string." }
```

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "`GET /chatz/1` (a typo in the path) and `GET /chats/999` (a chat that doesn't exist) both answer 404, so only the error body can tell the client which problem it hit.",
  "answer": true,
  "explanation": "Both are 404. The default body for an unmatched route is {\"detail\": \"Not Found\"}; your route's HTTPException should say something specific, like \"chat not found\" or a code." }
```

## 4. Testing error paths, and what a crash looks like

An error test should assert **status and body**. Status alone passes for the wrong reason surprisingly often: a 404 from a typo in the test's URL looks exactly like your "chat not found" 404.

```python
def test_unknown_chat_is_404():
    r = client.get("/chats/999")
    assert r.status_code == 404
    assert r.json() == {"detail": "chat not found"}
```

**Unhandled exceptions.** If a route crashes (a `KeyError`, say), a real server answers **500 Internal Server Error**. `TestClient` behaves differently by default: it **re-raises the exception inside your test**, so you see the real traceback instead of a bare 500:

```python
@app.get("/boom")
def boom():
    return {"x": {}["missing"]}
```

```console
$ # c = TestClient(app); c.get("/boom")
raised in test: KeyError('missing')
$ # TestClient(app, raise_server_exceptions=False).get("/boom")
500 Internal Server Error
```

The default is what you want while debugging. A test failing with a `KeyError` traceback from inside a route means "the route crashed", not "the test is wrong". Use `raise_server_exceptions=False` only when you want to check what a client would see.

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "In a pytest test using `TestClient(app)` with default settings, an unhandled KeyError in a route shows up as a response with status 500 that you can assert on.",
  "answer": false,
  "explanation": "By default TestClient re-raises the route's exception in the test, so the test fails with the KeyError traceback. Pass raise_server_exceptions=False to get the 500 response a real client would receive." }
```

```quiz
{ "id": "q6", "type": "choice", "label": "Debugging",
  "prompt": "`client.post(\"/chats/3/archive\")` fails with status 405 and `{\"detail\": \"Method Not Allowed\"}`. What is the most likely cause?",
  "options": ["Chat 3 doesn't exist", "The archive route exists but is declared with a different method, e.g. @app.put", "The request body is invalid", "The route raised an exception"], "answer": 1,
  "explanation": "405 means the path matched a route but not the method. A missing chat would be your 404, an invalid body 422, and a crash re-raises in the test." }
```

## 5. A debugging routine

When an endpoint test fails, read in this order before touching code:

1. **Status code.** 404 with `"Not Found"`: no route matched (typo, or the route isn't registered). 405: wrong method. 422: the request didn't fit the declared parameters. 200 where you expected an error: your error was never raised. An exception traceback: the route crashed.
2. **Error body.** For 422, `loc[0]` tells you where FastAPI *looked* for the value. If that's not where the client sent it, the declaration is wrong, not the client.
3. **The route declaration**: method, path, declaration order, parameter types and defaults. Most bugs in this module live there, not in the function body.

That's exactly the skill the exercise practises. You get a messages API with several bugs; each failing test points at one. Fix the code, not the tests.

```exercise
WEB.M01.L03.E1
```

```quiz
{ "id": "q7", "type": "explain", "label": "Debugging",
  "prompt": "A test expects 201 from `POST /chats` but gets 422 with `loc` `['body']`, type `model_attributes_type` and `input` `'title=x'`. The test sends `client.post(\"/chats\", data={\"title\": \"x\"})`. What's wrong, and where would you look?",
  "model": "loc ['body'] with model_attributes_type means the whole body wasn't a JSON object: FastAPI received the form-encoded string title=x. data= sends form data, not JSON, so the body model can't read the title. The test should use json={\"title\": \"x\"}. Here the bug is in the test, which is why you read the error before changing the route.",
  "explanation": "The FastAPI testing docs: JSON goes in json=, form data in data=." }
```
