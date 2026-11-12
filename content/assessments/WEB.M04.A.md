---
{ "id": "WEB.M04.A", "module": "WEB.M04", "title": "WEB.M04 module assessment: testing APIs with TestClient", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before WEB.M05.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI, Query\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\ndef get_greeting() -> str:\n    return \"hello\"\n\n@app.get(\"/greet\")\ndef greet(g: Annotated[str, Depends(get_greeting)], times: Annotated[int, Query(ge=1, le=3)] = 1):\n    return g * times\n\nclient = TestClient(app)\napp.dependency_overrides[get_greeting] = lambda: \"hi\"\nprint(client.get(\"/greet\", params={\"times\": 3}).json())\nprint(client.get(\"/greet\", params={\"times\": 4}).status_code)",
  "answer": "hihihi\n422",
  "explanation": "The override replaces get_greeting, so g is 'hi', repeated 3 times. times=4 is past le=3, so validation rejects it with 422 before the function runs." }
```

```quiz
{ "id": "a2", "type": "choice", "label": "Debugging",
  "prompt": "`test_list_is_empty` passes when run alone and fails in the full suite with `assert [{'id': 1, ...}] == []`. What do you fix first?",
  "options": ["Make the app fixture build a new app per test instead of sharing one created at import", "Add a time.sleep before the request", "Change the assert to `len(...) <= 1`", "Run the tests in alphabetical order"], "answer": 0,
  "explanation": "Passes alone, fails together: state leaks between tests. A fresh app per test (and teardown for overrides) removes the leak. Weakening the assert hides the problem." }
```

```quiz
{ "id": "a3", "type": "truefalse",
  "prompt": "`app.dependency_overrides[get_db()] = fake_db` overrides the get_db dependency.", "answer": false,
  "explanation": "get_db() calls the function, so the key is its return value, not the function. FastAPI looks overrides up by the original function object: dependency_overrides[get_db] = lambda: fake_db." }
```

```quiz
{ "id": "a4", "type": "choice",
  "prompt": "`page_size` is declared as `Query(ge=10, le=50)`. Which rows test its boundaries best?",
  "options": ["9 → 422, 10 → 200, 50 → 200, 51 → 422", "25 → 200", "0 → 422, 1000 → 422", "10 → 200, 50 → 200"], "answer": 0,
  "explanation": "An off-by-one bug moves one boundary by one step, so test the last invalid and the first valid value on each side." }
```

```quiz
{ "id": "a5", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\n@app.get(\"/boom\")\ndef boom():\n    raise KeyError(\"chat\")\n\nclient = TestClient(app, raise_server_exceptions=False)\nr = client.get(\"/boom\")\nprint(r.status_code)",
  "answer": "500",
  "explanation": "Nothing handles the KeyError, so the server answers 500. With raise_server_exceptions=False the test sees that response; with the default, the KeyError would be raised inside the test." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "`POST /chats/{chat_id}/members` adds a user (body: {\"user_id\": int > 0}) to a chat and sends them a push notification through a paid provider. Describe the tests you would write: the fixtures, what you fake and how, and one test for each kind of path (normal, invalid, edge, error).",
  "model": "Fixtures: app (fresh create_app() per test), client (with TestClient(app), teardown clears overrides), and a fake push sender installed via app.dependency_overrides[get_push] = lambda: fake, recording calls. Normal: add user 5 → 201, the member list contains 5, and fake.sent has exactly one notification. Invalid: user_id 0 or missing → 422, and fake.sent is empty (no side effect). Edge: adding a user who is already a member → whatever the spec says (200 or 409) and no second notification. Error: unknown chat → 404; push provider raising → the documented status (503 or 201 with the member still added, decide) via an override that raises.",
  "explanation": "Good answers fake only the external provider, assert side effects through the fake, and cover all four kinds of path." }
```
