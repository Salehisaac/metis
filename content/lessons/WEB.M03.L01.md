---
{
  "id": "WEB.M03.L01",
  "title": "Depends: shared parameters, sub-dependencies and settings",
  "difficulty": "intermediate",
  "minutes": 100,
  "prerequisites": ["WEB.M02"],
  "objectives": [
    "Extract repeated parameters into a dependency and reuse it through an Annotated alias",
    "Predict how often a dependency runs when several dependencies share it in one request",
    "Provide settings through an lru_cache-d dependency built from environment variables, and explain the cache's consequences",
    "Swap a dependency in tests with app.dependency_overrides and reset it"
  ],
  "why": "In go-zero, every handler gets a ServiceContext with config, models and clients, wired once in main. FastAPI's version is Depends: each endpoint declares what it needs, and the framework builds it per request. Done right, the same mechanism gives you configuration, shared parameters and, in the next lesson, database sessions and the current user, all swappable in tests with one line.",
  "applications": [
    "Pagination parameters shared by every list endpoint",
    "Configuration (limits, feature flags) read once from the environment",
    "Replacing real settings or services with test versions"
  ],
  "exercises": ["WEB.M03.L01.E1"],
  "sources": [
    {
      "title": "FastAPI Tutorial: Dependencies",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Dependency injection: code declares what it needs, FastAPI provides it", "Depends takes a single parameter, a function, which you don't call", "For each request FastAPI calls the dependency with the right parameters and passes the result", "An Annotated[..., Depends(...)] can be stored in a type alias and reused", "def and async def dependencies can be mixed freely", "Dependencies' parameters appear in the OpenAPI schema"]
    },
    {
      "title": "FastAPI Tutorial: Sub-dependencies",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/sub-dependencies/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Dependencies can have their own dependencies, as deep as needed", "A dependency used several times in one request is called only once and its value is cached for that request", "use_cache=False disables that cache"]
    },
    {
      "title": "FastAPI Advanced: Settings and Environment Variables",
      "url": "https://fastapi.tiangolo.com/advanced/settings/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Providing settings from a dependency makes them easy to override in tests", "@lru_cache on get_settings creates the Settings object only once", "Override with app.dependency_overrides[get_settings] = a function returning test settings", "The docs build Settings with the pydantic-settings package"]
    },
    {
      "title": "FastAPI Advanced: Testing Dependencies with Overrides",
      "url": "https://fastapi.tiangolo.com/advanced/testing-dependencies/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["app.dependency_overrides is a dict: original dependency -> override", "The override is used wherever the dependency is used", "Reset with app.dependency_overrides = {}"]
    },
    {
      "title": "functools: lru_cache",
      "url": "https://docs.python.org/3.12/library/functools.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["lru_cache memoises calls; cache_clear() clears the cache"]
    }
  ]
}
---
## 1. A dependency is a function FastAPI calls for you

Two list endpoints that both take `limit` and `offset` with the same bounds is the start of copy-paste drift. Put the parameters into a function, and let each endpoint **depend** on it:

```python
# contacts_api.py
import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel

app = FastAPI()

CONTACTS = [{"id": i, "name": n} for i, n in enumerate(["ali", "omid", "reza", "sara", "zahra"], start=1)]


def paging(
    limit: Annotated[int, Query(ge=1, le=50)] = 2,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return {"limit": limit, "offset": offset}


Paging = Annotated[dict, Depends(paging)]


@app.get("/contacts")
def list_contacts(page: Paging):
    start = page["offset"]
    return CONTACTS[start:start + page["limit"]]


@app.get("/contacts/search")
def search_contacts(q: str, page: Paging):
    found = [c for c in CONTACTS if q in c["name"]]
    return found[page["offset"]:page["offset"] + page["limit"]]
```

Driven with `TestClient`; the request is written on the left for readability, the script printed what follows `->`:

```console
GET /contacts                       -> [{'id': 1, 'name': 'ali'}, {'id': 2, 'name': 'omid'}]
GET /contacts?offset=2&limit=2      -> [{'id': 3, 'name': 'reza'}, {'id': 4, 'name': 'sara'}]
GET /contacts/search?q=a&limit=3    -> [{'id': 1, 'name': 'ali'}, {'id': 3, 'name': 'reza'}, {'id': 4, 'name': 'sara'}]
GET /contacts?limit=0               -> 422
```

How it works, per request: FastAPI sees `Depends(paging)`, reads `paging`'s own parameters (two query parameters, with their validation), calls `paging` with them, and passes the result in as `page`. The dependency's parameters become part of the endpoint: they're validated the same way and appear in `/docs`.

- **`Paging = Annotated[dict, Depends(paging)]`** is a plain Python type alias, and the docs recommend it. Every endpoint that says `page: Paging` gets the same dependency.
- **Pass the function, don't call it.** `Depends(paging)` is right. `Depends(paging())` calls `paging` once at import time and hands FastAPI the resulting dict.
- **Go comparison:** go-zero's `ServiceContext` is built once and shared by every handler. A FastAPI dependency is resolved **per request**, per endpoint that asks for it. That's why it can depend on the request's parameters.

```quiz
{ "id": "q1", "type": "choice", "label": "Debugging",
  "prompt": "A route declares `page: Annotated[dict, Depends(paging())]`. What happens?",
  "options": ["It works the same as Depends(paging)", "paging runs on every request twice", "Defining the route fails with TypeError: {'limit': 2, 'offset': 0} is not a callable object", "The query parameters are ignored and the defaults are always used, silently"], "answer": 2,
  "explanation": "paging() runs once while the module loads and returns a dict. Depends needs something callable, so FastAPI raises TypeError when the route is defined (run on the installed version). Pass the function itself." }
```

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.testclient import TestClient\n\ndef chat_filter(unread_only: bool = False, muted: bool = True):\n    return {\"unread_only\": unread_only, \"muted\": muted}\n\napp = FastAPI()\n\n@app.get(\"/chats\")\ndef list_chats(f: Annotated[dict, Depends(chat_filter)]):\n    return f\n\nprint(TestClient(app).get(\"/chats?unread_only=yes\").json())",
  "answer": "{'unread_only': True, 'muted': True}",
  "explanation": "The dependency's parameters are query parameters of the endpoint. unread_only=yes converts to True; muted keeps its default True." }
```

## 2. Sub-dependencies, and the per-request cache

A dependency can declare its own dependencies, as deep as you like. FastAPI resolves the whole tree. If **the same dependency appears twice in one request's tree**, it runs **once**, and both places get the same value:

```python
calls = []


def load_viewer():
    calls.append("load_viewer")
    return {"id": 1, "username": "ali"}


def viewer_lang(viewer: Annotated[dict, Depends(load_viewer)]):
    return "fa" if viewer["id"] == 1 else "en"


app = FastAPI()


@app.get("/inbox")
def inbox(viewer: Annotated[dict, Depends(load_viewer)], lang: Annotated[str, Depends(viewer_lang)]):
    return {"user": viewer["username"], "lang": lang}


c = TestClient(app)
print(c.get("/inbox").json())
print(c.get("/inbox").json())
print(calls)
```

```console
{'user': 'ali', 'lang': 'fa'}
{'user': 'ali', 'lang': 'fa'}
['load_viewer', 'load_viewer']
```

`load_viewer` is needed twice per request (by `inbox` and by `viewer_lang`) but ran once per request: two requests, two calls. That matters when the dependency hits a database or an auth service. The cache lives **only for one request**; the next request starts fresh. (`Depends(fn, use_cache=False)` turns it off, which you'll rarely need.)

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.testclient import TestClient\n\nopened = []\n\ndef db():\n    opened.append(1)\n    return \"conn\"\n\ndef chats_repo(conn: Annotated[str, Depends(db)]):\n    return f\"chats via {conn}\"\n\ndef users_repo(conn: Annotated[str, Depends(db)]):\n    return f\"users via {conn}\"\n\napp = FastAPI()\n\n@app.get(\"/dashboard\")\ndef dashboard(c: Annotated[str, Depends(chats_repo)], u: Annotated[str, Depends(users_repo)]):\n    return [c, u]\n\nclient = TestClient(app)\nprint(client.get(\"/dashboard\").json())\nclient.get(\"/dashboard\")\nprint(len(opened))",
  "answer": "['chats via conn', 'users via conn']\n2",
  "explanation": "Both repositories depend on db, but within one request db runs once and both get the same value. Two requests make two calls in total." }
```

## 3. Settings as a dependency

Configuration usually comes from environment variables. Reading `os.environ` inside every endpoint makes tests painful (you'd have to set variables before importing the app). The FastAPI docs' pattern: a `Settings` model, built by a `get_settings()` dependency decorated with `@lru_cache`.

```python
class Settings(BaseModel):
    app_name: str = "metis-chat"
    max_upload_mb: int = 10


@lru_cache
def get_settings() -> Settings:
    print("loading settings")
    return Settings(max_upload_mb=os.environ.get("CHAT_MAX_UPLOAD_MB", 10))


@app.get("/limits")
def limits(settings: Annotated[Settings, Depends(get_settings)]):
    return {"app": settings.app_name, "max_upload_mb": settings.max_upload_mb}
```

Run with `CHAT_MAX_UPLOAD_MB=25`, calling `/limits` twice:

```console
loading settings
{'app': 'metis-chat', 'max_upload_mb': 25}
{'app': 'metis-chat', 'max_upload_mb': 25}
```

- **The environment variable is a string `"25"`.** The Pydantic model converts it to an int (WEB.M02.L01), and an invalid value fails loudly at startup instead of halfway through a request.
- **`@lru_cache` makes it load once.** "loading settings" printed once for two requests. The docs say it "behaves almost as if it was just a global variable", but because it's a dependency, tests can replace it.
- **Consequence:** changing the environment *after* the first call has no effect until you call `get_settings.cache_clear()`. In tests that set environment variables, clear the cache first.
- The docs use `BaseSettings` from the `pydantic-settings` package, which reads the environment for you. It isn't installed in this academy, so we read `os.environ` explicitly. The dependency pattern is identical.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import os\nfrom functools import lru_cache\n\n@lru_cache\ndef max_members() -> int:\n    return int(os.environ.get(\"GROUP_MAX_MEMBERS\", \"200\"))\n\nos.environ[\"GROUP_MAX_MEMBERS\"] = \"500\"\nprint(max_members())\nos.environ[\"GROUP_MAX_MEMBERS\"] = \"1000\"\nprint(max_members())\nmax_members.cache_clear()\nprint(max_members())",
  "answer": "500\n500\n1000",
  "explanation": "The first call reads 500 and caches it. Changing the variable doesn't matter until cache_clear() forces the next call to read it again." }
```

## 4. Overriding dependencies in tests

`app.dependency_overrides` is a plain dict: **key = the original dependency function, value = a replacement function**. FastAPI then calls the replacement everywhere the original is used, including inside sub-dependencies:

```python
app.dependency_overrides[get_settings] = lambda: Settings(max_upload_mb=1)
print(c.get("/limits").json())
app.dependency_overrides = {}
print(c.get("/limits").json())
```

```console
{'app': 'metis-chat', 'max_upload_mb': 1}
{'app': 'metis-chat', 'max_upload_mb': 25}
```

The docs reset with `app.dependency_overrides = {}`. If you set an override inside a test, reset it at the end of that test, or it leaks into the next one. (A pytest fixture that yields and then resets is the clean way; WEB.M04 builds those.) In Go you'd pass a fake into the handler's constructor; here you swap the provider, and no endpoint code changes.

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "`app.dependency_overrides[get_settings] = fake_settings` affects only endpoints that declare `Depends(get_settings)` directly, not dependencies that use get_settings internally.",
  "answer": false,
  "explanation": "The override replaces get_settings wherever it appears in the dependency tree, including inside sub-dependencies. The docs: you can override a dependency used anywhere in the app." }
```

```quiz
{ "id": "q6", "type": "choice", "label": "Application",
  "prompt": "Why provide settings through `Depends(get_settings)` instead of a module-level `settings = Settings(...)` imported by every endpoint?",
  "options": ["It's faster, because lru_cache avoids the import", "A test can replace the settings with app.dependency_overrides without touching the environment or re-importing modules", "Module-level objects can't be Pydantic models", "FastAPI refuses global variables"], "answer": 1,
  "explanation": "With lru_cache it's effectively created once, like a global, but it's injected, so it can be swapped per test. A module-level object is fixed at import time." }
```

## 5. Your turn: settings-driven paging and a read-only switch

The exercise combines all three ideas in a message feed: `get_settings` reads limits from the environment, a paging dependency *depends on the settings* (the default and maximum page size are configurable, so a fixed `Query(le=...)` won't do), and a guard dependency blocks writes while the service is in read-only mode. The tests use `dependency_overrides` exactly as in section 4.

```exercise
WEB.M03.L01.E1
```
