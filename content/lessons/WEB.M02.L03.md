---
{
  "id": "WEB.M02.L03",
  "title": "Request and response models",
  "difficulty": "intermediate",
  "minutes": 100,
  "prerequisites": ["WEB.M02.L02"],
  "objectives": [
    "Split one resource into create, output and edit models, and say which fields belong in each",
    "Use response_model or a return annotation to filter what an endpoint sends, and say which wins when both are given",
    "Predict what happens when an endpoint returns data that doesn't fit its response model",
    "Implement a partial update (PATCH) with model_dump(exclude_unset=True), and explain why an explicit null must be blocked for fields that must not be null"
  ],
  "why": "The most common data leak in an API is an endpoint that returns the whole stored record: password hashes, emails, internal flags. The second most common bug is a PATCH that wipes the fields the client didn't send. Separate input and output models fix both, and they also make the API documentation tell the truth.",
  "applications": [
    "User endpoints that never return password hashes or other users' emails",
    "Partial edits of a profile or chat (PATCH)",
    "Accurate OpenAPI docs for the mobile team"
  ],
  "exercises": ["WEB.M02.L03.E1"],
  "sources": [
    {
      "title": "FastAPI Tutorial: Response Model - Return Type",
      "url": "https://fastapi.tiangolo.com/tutorial/response-model/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["A return type annotation or response_model is used to validate, document, serialise and filter the output", "If both are declared, response_model takes priority", "Use response_model when the function returns a different type than the declared output (e.g. a dict or an input model)", "Invalid return data means the app code is broken; FastAPI returns a server error instead of incorrect data", "Never send a user's password in a response; use a separate output model (UserIn/UserOut)", "response_model_exclude_unset returns only values that were explicitly set"]
    },
    {
      "title": "Pydantic: Models",
      "url": "https://pydantic.dev/docs/validation/latest/concepts/models/",
      "version": "Pydantic docs 'latest' (page states no version; installed 2.14.2)",
      "verified": "2026-11-12",
      "claims": ["model_dump returns a dict of the model's fields and values", "Extra data is ignored by default; extra='forbid' rejects it"]
    },
    {
      "title": "Pydantic: Validators",
      "url": "https://pydantic.dev/docs/validation/latest/concepts/validators/",
      "version": "Pydantic docs 'latest' (page states no version; installed 2.14.2)",
      "verified": "2026-11-12",
      "claims": ["A model_validator in after mode gets the instance and must return it", "Raising ValueError in a validator produces a validation error"]
    }
  ]
}
---
## 1. One resource, several models

In go-zero you'd write separate `CreateChatReq` and `ChatResp` types in the `.api` file, because what the client may *send* is not what it may *see*. Same idea here. For a chat:

| Model | Purpose | Fields |
|---|---|---|
| `ChatCreate` | body of POST | `title`, `invite_code` (secret, write-only) |
| `ChatOut` | every response | `id`, `title`, `description` |
| `ChatEdit` | body of PATCH | `title`, `description`, all optional |
| stored dict | internal | all of the above plus `owner_id` |

```python
# chats_api.py
import itertools

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

app = FastAPI()


class ChatCreate(BaseModel):
    title: str
    invite_code: str


class ChatOut(BaseModel):
    id: int
    title: str
    description: str | None = None


class ChatEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    description: str | None = None


chats: dict[int, dict] = {}
_ids = itertools.count(1)


@app.post("/chats", status_code=201, response_model=ChatOut)
def create_chat(body: ChatCreate):
    chat = {"id": next(_ids), "owner_id": 1, **body.model_dump()}
    chats[chat["id"]] = chat
    return chat


@app.get("/chats/{chat_id}")
def read_chat(chat_id: int) -> ChatOut:
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="chat not found")
    return chats[chat_id]


@app.patch("/chats/{chat_id}", response_model=ChatOut)
def edit_chat(chat_id: int, body: ChatEdit):
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="chat not found")
    changes = body.model_dump(exclude_unset=True)
    chats[chat_id].update(changes)
    return chats[chat_id]
```

## 2. response_model filters the output

`create_chat` returns the **whole stored dict**. The client receives only what `ChatOut` declares:

```python
c = TestClient(app)
print(c.post("/chats", json={"title": "Go devs", "invite_code": "x7Kq"}).json())
print(chats[1])
```

```console
{'id': 1, 'title': 'Go devs', 'description': None}
{'id': 1, 'owner_id': 1, 'title': 'Go devs', 'invite_code': 'x7Kq'}
```

`owner_id` and the secret `invite_code` are dropped; `description`, missing from storage, is filled with its default. FastAPI does four things with the output model: **validates** the returned data, **filters** it to the declared fields, **serialises** it to JSON, and **documents** it in `/docs`. The docs' own example is a `UserIn` with a password and a `UserOut` without, with the warning never to send a user's password in a response.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\nfrom pydantic import BaseModel\n\nclass MemberOut(BaseModel):\n    user_id: int\n    role: str = \"member\"\n\napp = FastAPI()\n\n@app.get(\"/chats/{chat_id}/members/{user_id}\", response_model=MemberOut)\ndef read_member(chat_id: int, user_id: int):\n    return {\"user_id\": user_id, \"phone\": \"+98 912 000 0000\", \"chat_id\": chat_id}\n\nprint(TestClient(app).get(\"/chats/4/members/9\").json())",
  "answer": "{'user_id': 9, 'role': 'member'}",
  "explanation": "Only MemberOut's fields are sent. phone and chat_id are filtered out; role isn't in the returned dict, so its default is used." }
```

## 3. Return annotation or response_model?

There are two ways to declare the output model:

- **Return annotation:** `def read_chat(...) -> ChatOut:` (`read_chat` above).
- **Decorator parameter:** `@app.post(..., response_model=ChatOut)` (`create_chat` above).

They do the same thing, and **if you give both, `response_model` wins**. The docs suggest `response_model` when the function returns something other than the output type. `create_chat` returns a `dict`, and in the docs' example the function returns the *input* model. In both cases an editor or type checker would complain about `-> ChatOut`. In this course: annotate when you return the output type; use `response_model` when you return a dict or another model.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "`@app.get(\"/me\", response_model=PublicProfile)` on `def me() -> PrivateProfile:`. Which model filters the response?",
  "options": ["PrivateProfile, because annotations are checked first", "PublicProfile, because response_model takes priority", "Both, one after the other", "Neither; FastAPI raises an error at startup"], "answer": 1,
  "explanation": "The FastAPI docs: if you declare both a return type and a response_model, the response_model takes priority." }
```

## 4. When your output is wrong: 500, not bad data

The output model is a contract *you* have to keep. If the returned data doesn't fit, FastAPI won't send it:

```python
@app.get("/chats/{chat_id}", response_model=ChatOut)   # ChatOut: id, title
def read_chat(chat_id: int):
    return {"id": chat_id, "name": "Go devs"}  # stored under the old column name
```

```console
$ # TestClient(app, raise_server_exceptions=False).get("/chats/1")
500 Internal Server Error
$ # TestClient(app).get("/chats/1"), the default
ResponseValidationError
[{'type': 'missing', 'loc': ('response', 'title'), 'msg': 'Field required', 'input': {'id': 1, 'name': 'Go devs'}}]
```

The docs' reasoning: invalid output means *your app code is broken*, so the client gets a server error rather than incorrect data. In a test, the default `TestClient` raises `ResponseValidationError`, and `loc` starts with `"response"`. When you see that, look at what your function returned, not at the request.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "If a path operation returns a dict that is missing a required field of its response_model, FastAPI sends the incomplete dict with status 200 and logs a warning.",
  "answer": false,
  "explanation": "The output is validated. Invalid output is treated as a bug in the app: the client gets 500, and with the default TestClient the test raises ResponseValidationError." }
```

## 5. PATCH: change only what was sent

`ChatEdit` has every field optional, because a PATCH sends only the fields it changes. But "optional" means absent fields get the default `None`, and a naive `chats[id].update(body.model_dump())` would overwrite the stored title with `None`. Pydantic remembers which fields were **actually set** by the input, and `model_dump(exclude_unset=True)` gives you only those:

```python
e = ChatEdit(description="Go and Python")
print(e.model_dump())
print(e.model_dump(exclude_unset=True))
print(ChatEdit(title=None).model_dump(exclude_unset=True))
```

```console
{'title': None, 'description': 'Go and Python'}
{'description': 'Go and Python'}
{'title': None}
```

An *explicit* `None` counts as set, so `{"description": null}` clears the description, while `{}` changes nothing. That's what clients expect from PATCH:

```python
print(c.patch("/chats/1", json={"description": "Go and Python"}).json())
print(c.patch("/chats/1", json={"title": "Gophers"}).json())
print(c.patch("/chats/1", json={"description": None}).json())
```

```console
{'id': 1, 'title': 'Go devs', 'description': 'Go and Python'}
{'id': 1, 'title': 'Gophers', 'description': 'Go and Python'}
{'id': 1, 'title': 'Gophers', 'description': None}
```

`extra="forbid"` on the edit model matters here. Without it, `{"titel": "x"}` would be a 200 that changes nothing.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "from pydantic import BaseModel\n\nclass NotifySettings(BaseModel):\n    sound: bool | None = None\n    preview: bool | None = None\n    mute_until: int | None = None\n\nstored = {\"sound\": True, \"preview\": True, \"mute_until\": 1700000000}\npatch = NotifySettings.model_validate({\"preview\": False, \"mute_until\": None})\nstored.update(patch.model_dump(exclude_unset=True))\nprint(stored)",
  "answer": "{'sound': True, 'preview': False, 'mute_until': None}",
  "explanation": "Only preview and mute_until were set (mute_until explicitly to None), so sound keeps its stored value. Without exclude_unset, sound would have been overwritten with None." }
```

## 6. The null trap in edit models

`ChatEdit.title` is `str | None`, so `{"title": null}` is valid input, and `exclude_unset` faithfully passes it on. The stored chat now has `title: None`, which `ChatOut` (where `title: str`) rejects:

```console
$ # c.patch("/chats/1", json={"title": None}), then c.get("/chats/1")
500 Internal Server Error
500 Internal Server Error
```

A client sent one bad request and broke the chat for everyone. "Optional in a PATCH" (may be absent) is not the same as "nullable" (may be cleared). The rule: **for a field that must never be null, an edit model has to reject an explicit `null` while still allowing the field to be absent.**

One way is a model validator that asks Pydantic which fields were actually sent. `model_fields_set` is the set behind `exclude_unset`:

```python
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator


class ChatEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def title_not_cleared(self):
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title cannot be null")
        return self


print(ChatEdit().model_dump(exclude_unset=True))
print(ChatEdit(description=None).model_dump(exclude_unset=True))
try:
    ChatEdit(title=None)
except ValidationError as e:
    print([(err["loc"], err["type"], err["msg"]) for err in e.errors()])
```

```console
{}
{'description': None}
[((), 'value_error', 'Value error, title cannot be null')]
```

`{"title": null}` is now rejected at the boundary, and `{"description": null}` still clears the description. One weakness: the error belongs to the **model**, so its `loc` is `()`, which FastAPI shows as `["body"]`. A client can't tell which field to highlight. Attaching the error to the field itself is possible with the tools from WEB.M02.L02 plus one fact about defaults, which the next quiz checks.

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "After a PATCH, `GET /chats/5` starts failing with 500 and the test shows `ResponseValidationError` with `loc` `('response', 'title')`, type `string_type`. What most likely happened?",
  "options": ["The GET request had an invalid chat id", "A PATCH stored title = None, which the output model doesn't allow", "The output model is missing the title field", "The client sent title as a query parameter"], "answer": 1,
  "explanation": "loc starts with 'response', so the stored data is the problem, not the request. string_type on title means the stored value isn't a string: an explicit null that the edit model let through." }
```

```quiz
{ "id": "q6", "type": "output",
  "prompt": "What does this print?",
  "code": "from pydantic import BaseModel, Field, ValidationError\n\nclass Mute(BaseModel):\n    minutes: int = Field(default=0, ge=1)\n\nprint(Mute().minutes)\ntry:\n    Mute(minutes=0)\nexcept ValidationError as e:\n    print(e.errors()[0][\"type\"])",
  "answer": "0\ngreater_than_equal",
  "explanation": "Defaults aren't validated: when the field is absent, the default 0 is used as is, even though it breaks ge=1. A value that is actually sent is validated. The same holds for validators: a field validator runs for a value that was sent, not for a default." }
```

## 7. Your turn: stop the user API from leaking

The exercise is a users API that works but uses one model and returns stored records directly. It leaks password hashes and emails, and its PATCH wipes fields. Refactor it with separate models so the tests (and the API docs) show only what each client should see.

```exercise
WEB.M02.L03.E1
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "A teammate says: \"We don't need an output model; I'll just `del user['password_hash']` before returning.\" Give two reasons to prefer a response model.",
  "model": "1) It's an allowlist, not a denylist: a field added to storage later (e.g. a reset token) is hidden automatically, while del only removes what you remembered. 2) It's declared once and applies to every path that returns the model, instead of a del in each endpoint. Also, it documents the real response shape in OpenAPI, and it validates the output, so a broken return is a 500, not corrupt data.",
  "explanation": "Output models filter by what's declared, which fails safe." }
```
