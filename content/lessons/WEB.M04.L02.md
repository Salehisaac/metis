---
{
  "id": "WEB.M04.L02",
  "title": "Fixtures for app and client, and dependency_overrides",
  "difficulty": "intermediate",
  "minutes": 60,
  "prerequisites": ["WEB.M04.L01"],
  "objectives": [
    "Explain why a test that passes alone but fails in the full run points to shared state",
    "Write app and client fixtures that give every test a fresh app, with cleanup after yield",
    "Share fixtures across test files with conftest.py, and predict the order in which fixtures set up and tear down",
    "Replace a dependency (clock, push sender, external API) with a fake through app.dependency_overrides, using the original function as the key"
  ],
  "why": "Tests that share state fail in random-looking ways: green on your machine, red in CI, green again when you rerun one test. Fixtures give every test its own world and clean it up afterwards. dependency_overrides is how you keep a test away from the network, the clock and paid APIs without changing the app's code: the FastAPI version of passing a fake to a Go constructor.",
  "applications": [
    "A conftest.py that every API test in a project uses",
    "Faking a payment, SMS or push provider in tests",
    "Freezing time so timestamps and expiry can be asserted exactly"
  ],
  "exercises": ["WEB.M04.L02.E1"],
  "sources": [
    {
      "title": "pytest: How to use fixtures",
      "url": "https://docs.pytest.org/en/stable/how-to/fixtures.html",
      "version": "pytest docs (stable); installed pytest 9.2.0",
      "verified": "2026-11-12",
      "claims": [
        "Tests request fixtures by declaring them as arguments; fixtures can request other fixtures",
        "Teardown code goes after the yield in a yield fixture",
        "function is the default scope: the fixture is destroyed at the end of the test",
        "A fixture requested more than once in the same test is not executed again for that test",
        "Fixtures in conftest.py are available to tests in multiple test modules of that directory"
      ]
    },
    {
      "title": "FastAPI Advanced: Testing Dependencies with Overrides",
      "url": "https://fastapi.tiangolo.com/advanced/testing-dependencies/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": [
        "app.dependency_overrides is a simple dict: the key is the original dependency function, the value is the override",
        "Reset overrides by setting app.dependency_overrides to an empty dict",
        "A dependency used anywhere in the app (path operation, decorator, include_router) can be overridden",
        "Typical use: an external provider that charges per request or is slow, replaced by a fake for tests"
      ]
    },
    {
      "title": "FastAPI Advanced: Testing Events: lifespan and startup - shutdown",
      "url": "https://fastapi.tiangolo.com/advanced/testing-events/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["Use TestClient in a with statement when the lifespan must run in tests"]
    }
  ]
}
---
## 1. Passes alone, fails together

Take the chats API from the last lesson. It keeps chats in a module-level dict, and the test file has one module-level `client`. Add a second test **above** the create test:

```python
def test_get_existing_chat():
    client.post("/chats", json={"title": "random"})

    response = client.get("/chats/1")

    assert response.status_code == 200


def test_create_chat_returns_201_and_the_chat():
    response = client.post("/chats", json={"title": "backend"})

    assert response.status_code == 201
    assert response.json() == {"id": 1, "title": "backend"}
```

```console
$ pytest -q test_order.py
E       AssertionError: assert {'id': 2, 'title': 'backend'} == {'id': 1, 'title': 'backend'}
E         Differing items:
E         {'id': 2} != {'id': 1}
1 failed, 1 passed, 1 warning in 0.16s
$ pytest -q "test_order.py::test_create_chat_returns_201_and_the_chat"
1 passed, 1 warning in 0.14s
```

Neither test is wrong on its own. The first test left a chat behind in the shared dict, so the second test's chat got id 2. In Go this is the package-level `var db = ...` that every test touches. The fix is the same in both languages: **every test builds its own world**.

Two changes make that possible:

1. **An app factory.** `create_app()` builds a new `FastAPI()` with its own state, instead of one `app` created at import time. You met this pattern in WEB.M03.
2. **Fixtures** that call the factory once per test.

```quiz
{ "id": "q1", "type": "choice", "label": "Debugging",
  "prompt": "CI fails test_b. On your machine, `pytest test_x.py::test_b` passes. What is the most likely cause?",
  "options": ["Another test changes shared state that test_b depends on", "CI uses a different Python version", "test_b is too slow", "pytest runs tests in parallel by default"], "answer": 0,
  "explanation": "Passes alone, fails in the full run: something that ran earlier left state behind (a module-level dict, an override, a row in a database). pytest runs tests one after another in file order unless a plugin changes that." }
```

## 2. Fixtures for app and client

A fixture is a function that pytest runs **for** a test that names it as a parameter. Go has no direct equivalent: it's like a setup helper plus `t.Cleanup`, wired up by name. Here's an invites endpoint that calls a paid push provider:

```python
# invites.py
class PushSender:
    """Sends mobile push notifications through a paid provider."""

    def send(self, user_id: int, text: str) -> None:
        raise RuntimeError("real network call: don't run this in tests")


def get_push() -> PushSender:
    return PushSender()


@router.post("/chats/{chat_id}/invites", status_code=201)
def invite(chat_id: int, body: InviteIn,
           members: Annotated[dict[int, set[int]], Depends(get_members)],
           push: Annotated[PushSender, Depends(get_push)]) -> dict:
    members.setdefault(chat_id, set()).add(body.user_id)
    push.send(body.user_id, f"you were added to chat {chat_id}")
    return {"chat_id": chat_id, "members": sorted(members[chat_id])}


def create_app() -> FastAPI:
    app = FastAPI()
    app.state.members = {1: {10}}  # chat 1 already has user 10
    app.include_router(router)
    return app
```

The fixtures go into `conftest.py`, next to the tests. pytest loads that file automatically, and every test file in the folder can use its fixtures without importing them:

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient

from invites import create_app, get_push


@pytest.fixture
def app():
    print("\n[app] new app")
    return create_app()


@pytest.fixture
def client(app):
    print("[client] open")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    print("[client] closed, overrides cleared")
```

- `client(app)` requests the `app` fixture, the same way a test does.
- **Everything after `yield` is teardown.** It runs when the test ends, even if the test failed. That's the `defer` or `t.Cleanup` of pytest.
- `with TestClient(app) as c:` runs the app's lifespan (startup and shutdown). Real apps often open a database pool there; without `with`, that code doesn't run.
- The default scope is `function`: a new `app` for every test. pytest **caches a fixture within one test**, so the test, `client` and any other fixture that asks for `app` all get the same object.

`-s` shows the prints, so you can see the order with two tests:

```console
$ pytest -q -s
[app] new app
[client] open
.[client] closed, overrides cleared
[app] new app
[client] open
.[client] closed, overrides cleared
2 passed, 1 warning in 0.04s
```

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "A test requests `client` and `app`, and `client` also requests `app`. pytest calls the `app` fixture twice for that test, so the test and the client see different apps.", "answer": false,
  "explanation": "Within one test, pytest runs each fixture once and reuses the result. The test and the client share the same app, which is what makes `app.state` and `app.dependency_overrides` useful in tests." }
```

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "In the conftest.py above, the test function raises an AssertionError. What happens to the line `app.dependency_overrides.clear()`?",
  "options": ["It still runs, as teardown after the test", "It's skipped because the test failed", "It runs before the test", "It runs only once, at the end of the session"], "answer": 0,
  "explanation": "Code after yield in a fixture is teardown, and pytest runs it whether the test passed or failed, like defer in Go." }
```

## 3. Replacing a dependency: `app.dependency_overrides`

`app.dependency_overrides` is a plain dict on the app. **The key is the original dependency function, and the value is the function FastAPI should call instead.** Nothing in `invites.py` changes:

```python
# conftest.py (continued)
class FakePush:
    def __init__(self):
        self.sent = []

    def send(self, user_id, text):
        self.sent.append((user_id, text))


@pytest.fixture
def push(app):
    fake = FakePush()
    app.dependency_overrides[get_push] = lambda: fake
    return fake
```

```python
# test_invites.py
def test_invite_adds_member_and_notifies(client, push):
    response = client.post("/chats/1/invites", json={"user_id": 11})

    assert response.status_code == 201
    assert response.json() == {"chat_id": 1, "members": [10, 11]}
    assert push.sent == [(11, "you were added to chat 1")]


def test_invalid_user_id_sends_nothing(client, push):
    response = client.post("/chats/1/invites", json={"user_id": 0})

    assert response.status_code == 422
    assert push.sent == []
```

- The fake *records* calls, so a test can assert on a side effect ("the user was notified exactly once") that never appears in the HTTP response.
- The second test asserts that **nothing** was sent. An invalid request must have no side effects, and only a fake can show that.
- The override lives on this test's `app`, and the `client` fixture clears it in teardown. Clearing matters as soon as an app is shared, for example with a wider fixture scope.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.testclient import TestClient\n\ndef get_region() -> str:\n    return \"eu\"\n\napp = FastAPI()\n\n@app.get(\"/region\")\ndef region(r: Annotated[str, Depends(get_region)]):\n    return r\n\nclient = TestClient(app)\napp.dependency_overrides[get_region] = lambda: \"us\"\nprint(client.get(\"/region\").json())\napp.dependency_overrides.clear()\nprint(client.get(\"/region\").json())",
  "answer": "us\neu",
  "explanation": "FastAPI looks up the override on every request. With the override installed, it calls the lambda; after clear(), the original get_region runs again." }
```

```quiz
{ "id": "q5", "type": "output", "label": "Debugging",
  "prompt": "Only one pair of parentheses differs from the previous quiz. What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.testclient import TestClient\n\ndef get_region() -> str:\n    return \"eu\"\n\napp = FastAPI()\n\n@app.get(\"/region\")\ndef region(r: Annotated[str, Depends(get_region)]):\n    return r\n\nclient = TestClient(app)\napp.dependency_overrides[get_region()] = lambda: \"us\"\nprint(client.get(\"/region\").json())",
  "answer": "eu",
  "explanation": "get_region() calls the function, so the key is the string \"eu\", not the function. FastAPI never finds an override for get_region, so the real one runs. There's no error, which is why this mistake is easy to miss: the key must be the function object itself." }
```

## 4. Common mistakes

- **App or client at module level** (`client = TestClient(create_app())` at the top of a test file). It's built once per process and shared by every test, which brings back section 1's problem.
- **Overriding but never clearing.** It works until two tests share an app, then the second test silently uses the first test's fake.
- **Overriding with a value instead of a function:** `app.dependency_overrides[get_push] = FakePush()`. FastAPI *calls* the override, so this calls the FakePush instance, which fails with a TypeError. Use `lambda: fake`.
- **Faking too much.** Override what is slow, paid, random or external (clock, network, third-party APIs). Keep your own validation and logic real; that's what the test is for.

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "Which dependency should you NOT replace with a fake in an endpoint test?",
  "options": ["The Pydantic model that validates the request body", "A client for a third-party SMS API", "get_clock, which returns the current time", "A function that generates random invite codes"], "answer": 0,
  "explanation": "Validation is part of the behaviour you're testing. The other three are external, time-based or random, which makes tests slow, costly or unrepeatable, so they're good candidates for a fake." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "A teammate's conftest.py has `app = create_app()` and `client = TestClient(app)` at the top, and a fixture that sets an override without removing it. Tests pass locally but fail in CI, where a plugin runs them in a random order. Explain the failures and the fix in three or four sentences.",
  "model": "The app and its state are created once at import, so every test shares them; with a different order, a test sees data or an override left behind by an earlier test. The fix: an app fixture that calls create_app() per test, a client fixture that yields a TestClient inside a with block, and teardown after yield that clears dependency_overrides. Then each test starts from the same clean state in any order.",
  "explanation": "Order-dependent tests always come from shared state; fixtures with teardown remove it." }
```

## 5. Your turn

The exercise is a **debugging** task: every test passes alone, and four fail together. Fix `conftest.py` only.

```exercise
WEB.M04.L02.E1
```
