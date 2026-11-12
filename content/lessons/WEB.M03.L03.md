---
{
  "id": "WEB.M03.L03",
  "title": "Splitting the app: APIRouter, services and repositories",
  "difficulty": "intermediate",
  "minutes": 110,
  "prerequisites": ["WEB.M03.L02"],
  "objectives": [
    "Split an app into routers, services, a repository and a dependencies module, and say what belongs in each",
    "Group endpoints with APIRouter (prefix, tags, router-level dependencies) and include them in the app",
    "Keep services free of FastAPI so they can be tested without HTTP, and translate their exceptions into status codes at the edge",
    "Wire repository and service through Depends, and give each test its own repository with dependency_overrides"
  ],
  "why": "A real messaging backend has dozens of endpoints. In one file, HTTP details, business rules and storage blur together, and changing the storage (WEB.M05) means touching every endpoint. The layout you know from go-zero (handler, logic, svc context, model) exists in FastAPI too; this lesson builds it with routers, services and dependencies, which is also the shape the projects use.",
  "applications": [
    "A codebase where WEB.M05 swaps in-memory storage for SQL without touching routers",
    "Fast unit tests of business rules, without a client",
    "Router-level auth for a whole group of endpoints"
  ],
  "exercises": ["WEB.M03.L03.E1"],
  "sources": [
    {
      "title": "FastAPI Tutorial: Bigger Applications - Multiple Files",
      "url": "https://fastapi.tiangolo.com/tutorial/bigger-applications/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["APIRouter is a 'mini FastAPI' with the same options", "prefix, tags, dependencies and responses on APIRouter apply to all its path operations", "The prefix must not end with /", "Router dependencies run first, then decorator dependencies, then parameter dependencies", "app.include_router adds a router's routes to the app; it can take its own prefix, tags and dependencies", "The docs' layout: app/main.py, app/dependencies.py, app/routers/*.py, with __init__.py files and relative imports"]
    },
    {
      "title": "FastAPI Tutorial: Dependencies",
      "url": "https://fastapi.tiangolo.com/tutorial/dependencies/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Dependencies can have sub-dependencies; FastAPI resolves the whole tree", "Annotated dependency aliases can be reused"]
    },
    {
      "title": "FastAPI Advanced: Testing Dependencies with Overrides",
      "url": "https://fastapi.tiangolo.com/advanced/testing-dependencies/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Overrides apply to a dependency used anywhere: path operation, decorator, include_router", "Reset with app.dependency_overrides = {}"]
    }
  ]
}
---
## 1. Four kinds of code, four places

In go-zero, `goctl` generates a fixed layout: `handler` (HTTP), `logic` (business rules), `svc` (the ServiceContext that holds dependencies) and `model` (storage). FastAPI doesn't generate anything, but the same split works, and it's what this course uses from now on:

| Layer | go-zero | Here | Knows about HTTP? |
|---|---|---|---|
| router | `handler` | `app/routers/contacts.py` (an `APIRouter`) | yes: paths, status codes, request and response models |
| service | `logic` | `app/services.py` | **no**: plain Python, raises domain exceptions |
| repository | `model` | `app/repository.py` | no: stores and loads rows |
| wiring | `svc.ServiceContext` | `app/dependencies.py` (`Depends` functions) | only for reading headers or settings |

The rule that makes it work: **dependencies point inwards.** Routers import services; services import repositories; nothing imports routers except `main.py`. The service never imports `fastapi`.

The example is a contacts book for the messenger, laid out like the FastAPI docs (every folder has an `__init__.py`, which makes it a package):

```console
app/
├── __init__.py
├── main.py           # creates the app, includes routers
├── dependencies.py   # get_contact_repo, get_contact_service, get_user_id
├── repository.py     # ContactRepository (in memory until WEB.M05)
├── services.py       # ContactService + DuplicateContact
└── routers/
    ├── __init__.py
    └── contacts.py   # APIRouter(prefix="/contacts")
```

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A rule says a user can't add more than 500 contacts. Where should that check live?",
  "options": ["In the router, before calling the service", "In the service, raising a domain exception that the router (or a handler) maps to a status code", "In the repository's add method", "In a Pydantic model on the request body"], "answer": 1,
  "explanation": "It's a business rule, so it belongs in the service, where a CLI import or a queue consumer gets the same rule. The router only translates the exception into HTTP. The repository should stay dumb storage, and a body model can't see how many contacts exist." }
```

## 2. Repository and service: no FastAPI here

```python
# app/repository.py
import itertools


class ContactRepository:
    """In-memory storage. WEB.M05 replaces it with a database-backed class with the same methods."""

    def __init__(self):
        self._rows: dict[int, dict] = {}
        self._ids = itertools.count(1)

    def add(self, owner_id: int, phone: str, name: str) -> dict:
        row = {"id": next(self._ids), "owner_id": owner_id, "phone": phone, "name": name}
        self._rows[row["id"]] = row
        return row

    def by_owner(self, owner_id: int) -> list[dict]:
        return [r for r in self._rows.values() if r["owner_id"] == owner_id]
```

```python
# app/services.py
from .repository import ContactRepository


class DuplicateContact(Exception):
    pass


class ContactService:
    """Business rules only: no FastAPI, no HTTP status codes."""

    def __init__(self, repo: ContactRepository):
        self.repo = repo

    def add_contact(self, owner_id: int, phone: str, name: str) -> dict:
        normalised = phone.replace(" ", "")
        if any(c["phone"] == normalised for c in self.repo.by_owner(owner_id)):
            raise DuplicateContact(normalised)
        return self.repo.add(owner_id, normalised, name.strip())

    def contacts_of(self, owner_id: int) -> list[dict]:
        return sorted(self.repo.by_owner(owner_id), key=lambda c: c["name"].casefold())
```

The service gets its repository **through the constructor**, exactly like a Go struct that holds an interface field. That makes it testable with no web framework at all:

```python
from app.repository import ContactRepository
from app.services import ContactService, DuplicateContact

service = ContactService(ContactRepository())
service.add_contact(7, "+1 555 0100", "Zed")
service.add_contact(7, "+1 555 0199", "amir")
print([c["name"] for c in service.contacts_of(7)])
try:
    service.add_contact(7, "+15550100", "Zed twice")
except DuplicateContact as exc:
    print("duplicate:", exc)
```

```console
['amir', 'Zed']
duplicate: +15550100
```

`from .repository import ...` is a **relative import**: "the `repository` module in my own package". The docs' layout uses these, so the package works no matter where it's installed. No `Protocol` or abstract base class for the repository yet: there's one implementation. When WEB.M05 adds a second, an interface earns its place.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "This is a stand-alone version of the service's sorting rule. What does it print?",
  "code": "contacts = [{\"name\": \"Zed\"}, {\"name\": \"amir\"}, {\"name\": \"Bita\"}]\nprint([c[\"name\"] for c in sorted(contacts, key=lambda c: c[\"name\"])])\nprint([c[\"name\"] for c in sorted(contacts, key=lambda c: c[\"name\"].casefold())])",
  "answer": "['Bita', 'Zed', 'amir']\n['amir', 'Bita', 'Zed']",
  "explanation": "Plain string order puts every capital letter before every lower-case letter. casefold() compares case-insensitively, which is what people expect in a contact list. This is the kind of rule worth a fast service-level test." }
```

## 3. Wiring: the dependencies module

```python
# app/dependencies.py
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from .repository import ContactRepository
from .services import ContactService


@lru_cache
def get_contact_repo() -> ContactRepository:
    return ContactRepository()  # one shared in-memory store for the whole process


def get_contact_service(repo: Annotated[ContactRepository, Depends(get_contact_repo)]) -> ContactService:
    return ContactService(repo)


def get_user_id(x_user_id: Annotated[int | None, Header()] = None) -> int:
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return x_user_id  # fake auth until WEB.M06
```

This module is the ServiceContext of the app. `get_contact_repo` is cached (L01's settings pattern), so every request shares one in-memory store. `get_contact_service` is cheap and built per request around it. In WEB.M05, `get_contact_repo` becomes a `yield` dependency around a database session (L02's pattern), and **nothing else changes**.

## 4. The router

```python
# app/routers/contacts.py
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import get_contact_service, get_user_id
from ..services import ContactService, DuplicateContact

router = APIRouter(prefix="/contacts", tags=["contacts"], dependencies=[Depends(get_user_id)])

Service = Annotated[ContactService, Depends(get_contact_service)]
UserId = Annotated[int, Depends(get_user_id)]


class NewContact(BaseModel):
    phone: str
    name: str


@router.post("", status_code=201)
def add_contact(body: NewContact, user_id: UserId, service: Service):
    try:
        return service.add_contact(user_id, body.phone, body.name)
    except DuplicateContact:
        raise HTTPException(status_code=409, detail="contact already exists")


@router.get("")
def list_contacts(user_id: UserId, service: Service):
    return service.contacts_of(user_id)
```

```python
# app/main.py
from fastapi import FastAPI

from .routers import contacts

app = FastAPI()
app.include_router(contacts.router)
```

- **`APIRouter`** takes the same options as the app, the docs call it a "mini FastAPI". `prefix="/contacts"` is prepended to every path in it. The prefix **must not end with `/`**. Here the routes use `""`, so the full path is exactly `/contacts`.
- **`tags`** group the endpoints in `/docs`.
- **`dependencies=[Depends(get_user_id)]`** on the router runs for every endpoint in it, before the endpoint's own dependencies. That's the docs' way to require authentication for a whole group. The endpoints still declare `UserId` because they need the value; the per-request cache resolves it once.
- **The router translates domain exceptions into HTTP** (`DuplicateContact` → 409). With many of them, use the exception handlers from WEB.M02.L04 instead of `try/except` in each route.
- `..dependencies` means "go up from `app/routers` to `app`, then `dependencies`".

Running it with `TestClient` from the folder that contains `app/` (request on the left for readability; the script printed what follows `->`, and the last line printed each path's tags from `app.openapi()`):

```console
POST /contacts {"phone": "+98 912 000 1111", "name": " Sara "}  X-User-Id: 1 -> {'id': 1, 'owner_id': 1, 'phone': '+989120001111', 'name': 'Sara'}
POST /contacts {"phone": "+98912 0001111", ...}                  X-User-Id: 1 -> 409
GET  /contacts  (no header)                                                    -> 401
paths and tags in /openapi.json: {'/contacts': [['contacts'], ['contacts']]}
```

The second POST is a duplicate only *after* normalising the spaces, a rule that lives in the service. The GET without a header is stopped by the router-level dependency.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import APIRouter, FastAPI\nfrom fastapi.testclient import TestClient\n\nrouter = APIRouter(prefix=\"/chats\", tags=[\"chats\"])\n\n@router.get(\"/{chat_id}/pins\")\ndef pins(chat_id: int):\n    return {\"chat_id\": chat_id, \"pins\": []}\n\napp = FastAPI()\napp.include_router(router, prefix=\"/api/v1\")\nc = TestClient(app)\nprint(c.get(\"/api/v1/chats/5/pins\").json())\nprint(c.get(\"/chats/5/pins\").status_code)",
  "answer": "{'chat_id': 5, 'pins': []}\n404",
  "explanation": "include_router's prefix is added in front of the router's own prefix, so the path is /api/v1/chats/{chat_id}/pins. Without /api/v1 nothing matches: 404." }
```

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "`APIRouter(prefix=\"/contacts/\")` is the recommended way to declare a prefix, because paths inside the router start with `/`.",
  "answer": false,
  "explanation": "The docs say the prefix must not end with /. Path operations already start with /, so the prefix is /contacts." }
```

## 5. Tests: a fresh repository per test

Because the repository is a dependency, a test can give the app its own empty one. Create it **once per test** and return that same object, or every request gets a new empty store:

```python
from fastapi.testclient import TestClient

from app.dependencies import get_contact_repo
from app.main import app
from app.repository import ContactRepository


def test_contacts_are_listed_by_name():
    repo = ContactRepository()
    app.dependency_overrides[get_contact_repo] = lambda: repo
    c = TestClient(app)
    me = {"X-User-Id": "1"}
    c.post("/contacts", json={"phone": "+1 555 0100", "name": "Zed"}, headers=me)
    c.post("/contacts", json={"phone": "+1 555 0199", "name": "amir"}, headers=me)
    assert [x["name"] for x in c.get("/contacts", headers=me).json()] == ["amir", "Zed"]
    app.dependency_overrides = {}
```

```console
$ pytest -q test_contacts.py
1 passed, 1 warning in 0.16s   # the warning is the harmless httpx deprecation notice
```

Two kinds of tests now exist, and you want both:

- **Service tests** (section 2): no client, no HTTP, milliseconds each. Use them for every rule and edge case.
- **API tests** through `TestClient`: fewer, checking that routes, status codes, auth and wiring are connected correctly.

WEB.M04 turns this into pytest fixtures.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "A test overrides a store dependency in two different ways. What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import APIRouter, Depends, FastAPI\nfrom fastapi.testclient import TestClient\n\nclass Store:\n    def __init__(self):\n        self.items = []\n\ndef get_store() -> Store:\n    return Store()\n\nrouter = APIRouter(prefix=\"/drafts\")\n\n@router.post(\"\", status_code=201)\ndef save(text: str, store: Annotated[Store, Depends(get_store)]):\n    store.items.append(text)\n    return len(store.items)\n\n@router.get(\"\")\ndef drafts(store: Annotated[Store, Depends(get_store)]):\n    return store.items\n\napp = FastAPI()\napp.include_router(router)\nc = TestClient(app)\napp.dependency_overrides[get_store] = Store\nprint(c.post(\"/drafts?text=hi\").json(), c.get(\"/drafts\").json())\nshared = Store()\napp.dependency_overrides[get_store] = lambda: shared\nprint(c.post(\"/drafts?text=hi\").json(), c.get(\"/drafts\").json())",
  "answer": "1 []\n1 ['hi']",
  "explanation": "Overriding with the class Store means FastAPI calls Store() on every request, so the GET sees a brand-new empty store. Returning one shared object from a lambda keeps state across the requests of one test." }
```

## 6. Your turn: split a chat-folders service

The exercise gives you a finished repository and `main.py`. You write the service (the folder rules, with no FastAPI), the dependencies module and the router. The tests check the service on its own, the HTTP behaviour, the router's prefix and tags, and that each test can inject its own repository. Because the course's exercise checker copies single files, the modules sit side by side (`services.py`, `deps.py`, `folders_router.py`) instead of in an `app/` package, and they use plain `import services` instead of relative imports. The layering is the same.

```exercise
WEB.M03.L03.E1
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "A teammate puts `from fastapi import HTTPException` in the service and raises 409 there, \"to save the try/except in the router\". What's the cost?",
  "model": "The service is then tied to HTTP: a CLI import job, a Kafka consumer or a gRPC endpoint calling the same service gets HTTP exceptions that mean nothing to them, and service tests have to know status codes. Domain exceptions keep the rule reusable; the HTTP mapping lives once at the edge (router or exception handler).",
  "explanation": "Keep the dependency direction pointing inwards: HTTP knows about the domain, not the other way round." }
```
