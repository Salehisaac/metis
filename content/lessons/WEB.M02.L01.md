---
{
  "id": "WEB.M02.L01",
  "title": "Pydantic models: parsing, coercion and ValidationError",
  "difficulty": "beginner",
  "minutes": 90,
  "prerequisites": ["WEB.M01"],
  "objectives": [
    "Define a BaseModel with required, optional and defaulted fields, and say which inputs make each one fail",
    "Predict which input values Pydantic converts (\"42\" to 42) and which it rejects (3.5 for int, 5 for str)",
    "Read ValidationError.errors() and relate its loc to the loc in FastAPI's 422 body",
    "Reject unknown fields with extra=\"forbid\" and explain the mass-assignment risk it prevents",
    "Use model_validate, model_dump and model_dump_json, and know that plain assignment isn't validated"
  ],
  "why": "In WEB.M01 you declared a BaseModel and FastAPI rejected bad bodies for you. That was Pydantic working behind the scenes. Knowing its rules directly tells you exactly what a model accepts, so you can predict your API's 422s, validate data that doesn't come through HTTP (imports, queue messages, config) and avoid fields a client was never supposed to set.",
  "applications": [
    "Request bodies in FastAPI",
    "Validating imported or queued data (a chat export, a Kafka message) before it touches the database",
    "Blocking clients from setting fields like is_admin"
  ],
  "exercises": ["WEB.M02.L01.E1"],
  "sources": [
    {
      "title": "Pydantic: Models",
      "url": "https://pydantic.dev/docs/validation/latest/concepts/models/",
      "version": "Pydantic docs 'latest' (page states no version; installed 2.14.2)",
      "verified": "2026-11-12",
      "claims": ["Models are classes inheriting from BaseModel with fields as annotated attributes", "Pydantic raises ValidationError whenever it finds an error in the data", "Pydantic may cast input data to the field type: the string '123' becomes the int 123", "Extra data is ignored by default; extra='forbid' makes it an error", "model_validate validates a dict or model instance; model_dump returns a dict; model_dump_json returns a JSON string"]
    },
    {
      "title": "Pydantic: Fields",
      "url": "https://pydantic.dev/docs/validation/latest/concepts/fields/",
      "version": "Pydantic docs 'latest' (page states no version; installed 2.14.2)",
      "verified": "2026-11-12",
      "claims": ["Defaults use normal assignment syntax", "A non-hashable default (such as a list) is deep-copied for each instance"]
    },
    {
      "title": "FastAPI Tutorial: Request Body",
      "url": "https://fastapi.tiangolo.com/tutorial/body/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["FastAPI reads the body as JSON, converts types and validates using the Pydantic model", "A field with a default is not required; the default, not the `| None`, is what makes it optional"]
    }
  ]
}
---
## 1. A model is a parser with a type

In Go, a request body is a struct with JSON tags, decoded with `json.Unmarshal`, and then checked (by hand, or with a validator library and struct tags). Unmarshal and validation are two separate steps, and nothing stops you from using the struct before the second step.

A Pydantic model merges them. **Creating the object *is* the validation.** If you hold a `Profile`, its fields have the declared types:

```python
from pydantic import BaseModel, ValidationError


class Profile(BaseModel):
    user_id: int
    username: str
    bio: str | None = None
    langs: list[str] = []


p = Profile(user_id="42", username="sara", langs=["go", "python"])
print(repr(p))
print(p.user_id + 1)
```

```console
Profile(user_id=42, username='sara', bio=None, langs=['go', 'python'])
43
```

`"42"` became the int `42`. Pydantic converts input when the conversion is unambiguous; the docs call this casting input data to conform to the field types. That's why `"42"` from a URL or a form works. It's also why `p.user_id + 1` is safe: by the time you have `p`, `user_id` **is** an int.

The mutable default `langs: list[str] = []` is fine here, unlike in a plain function (PY.M04). Pydantic copies a non-hashable default for each instance, so two profiles never share one list.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from pydantic import BaseModel\n\nclass Reaction(BaseModel):\n    message_id: int\n    emoji: str\n\nr = Reaction(message_id=\"12\", emoji=\"ok\")\nprint(r.message_id * 2)",
  "answer": "24",
  "explanation": "\"12\" is converted to the int 12 when the model is created, so the result is 24, not \"1212\"." }
```

## 2. What converts and what doesn't

The conversion is deliberately limited: it never loses information or guesses.

```python
try:
    Profile(user_id="forty-two", langs="go")
except ValidationError as e:
    print(e.error_count(), "errors")
    for err in e.errors():
        print(err["loc"], err["type"], repr(err["input"]))
```

```console
3 errors
('user_id',) int_parsing 'forty-two'
('username',) missing {'user_id': 'forty-two', 'langs': 'go'}
('langs',) list_type 'go'
```

Rules worth memorising, all checked on the installed Pydantic 2.14:

| Input → field type | Result |
|---|---|
| `"42"` → `int` | `42` |
| `"forty-two"` → `int` | error `int_parsing` |
| `3.5` → `int` | error `int_from_float` (it would lose the `.5`) |
| `2.0` → `int` | `2` (nothing lost) |
| `5` → `str` | error `string_type`: numbers are **not** turned into strings |
| `"go"` → `list[str]` | error `list_type`: a string is not wrapped into a list |

Like FastAPI, Pydantic collects **all** errors before raising, so a client fixes everything in one round trip.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "from pydantic import BaseModel, ValidationError\n\nclass Reaction(BaseModel):\n    message_id: int\n    emoji: str\n\ntry:\n    Reaction(message_id=3.5, emoji=7)\nexcept ValidationError as exc:\n    print([(e[\"loc\"][0], e[\"type\"]) for e in exc.errors()])",
  "answer": "[('message_id', 'int_from_float'), ('emoji', 'string_type')]",
  "explanation": "3.5 can't become an int without losing data, and an int is never converted to str. Both errors are reported together." }
```

## 3. Required, optional, nullable

Two separate questions, and Python's syntax answers each one in a different place:

- **Must the key be present?** Decided by the **default**. No default → required.
- **May the value be `null`/`None`?** Decided by the **type**. `| None` → `None` is allowed.

| Declaration | Key absent | `None` given |
|---|---|---|
| `bio: str` | error `missing` | error `string_type` |
| `bio: str \| None = None` | `None` | `None` |
| `bio: str \| None` (no default) | error `missing` | `None` |
| `bio: str = ""` | `""` | error `string_type` |

The third row surprises most people: `int | None` without a default is **required but nullable**. The client must send the key, even if its value is `null`. The FastAPI docs make the same point: it's the default that makes a field optional, not the `| None`.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "In `class Msg(BaseModel): reply_to: int | None`, calling `Msg()` with no arguments works and sets reply_to to None.",
  "answer": false,
  "explanation": "With no default, the field is required: Msg() raises ValidationError with type missing. `| None` only allows the value None; `= None` makes the key optional." }
```

## 4. Unknown fields: ignored, unless you forbid them

By default Pydantic **silently drops** fields the model doesn't declare. Usually that's harmless. For write endpoints it can hide mistakes (a client sends `biography` instead of `bio` and wonders why nothing changes), and it matters for security once you copy request data onto stored objects. `model_config = ConfigDict(extra="forbid")` turns unknown fields into errors:

```python
from pydantic import BaseModel, ConfigDict, ValidationError


class ProfileUpdate(BaseModel):
    bio: str | None = None


class StrictProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bio: str | None = None


payload = {"bio": "backend dev", "is_admin": True}
print(ProfileUpdate.model_validate(payload))
try:
    StrictProfileUpdate.model_validate(payload)
except ValidationError as e:
    print([(err["loc"], err["type"]) for err in e.errors()])
```

```console
bio='backend dev'
[(('is_admin',), 'extra_forbidden')]
```

The risk it guards against is called **mass assignment**: code that does `user.update(request_json)` lets a client set `is_admin`. A model that only declares `bio` already protects you if you use the model's data rather than the raw JSON. `extra="forbid"` adds a loud error, so a typo or an attack shows up as a 422 instead of being quietly ignored.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "`class ChatUpdate(BaseModel): title: str` with no model_config. A client sends `{\"title\": \"Team\", \"owner_id\": 1}`. What happens on `ChatUpdate.model_validate(...)`?",
  "options": ["ValidationError: owner_id is not declared", "The model is created with title='Team'; owner_id is silently dropped", "The model is created and has an extra owner_id attribute", "owner_id replaces title"], "answer": 1,
  "explanation": "The default is to ignore extra data. Only extra=\"forbid\" makes it an error." }
```

## 5. In and out: model_validate, model_dump, model_dump_json

```python
p = Profile.model_validate({"user_id": 7, "username": "omid"})
print(p.model_dump())
print(p.model_dump_json())
p.user_id = "not a number"
print(repr(p.user_id))
```

```console
{'user_id': 7, 'username': 'omid', 'bio': None, 'langs': []}
{"user_id":7,"username":"omid","bio":null,"langs":[]}
'not a number'
```

- **`Model.model_validate(data)`** validates a dict you already have (from `json.loads`, a queue, a CSV row). It's the same as `Model(**data)`, but it also works when `data` isn't a dict, and then reports a proper error instead of a `TypeError`.
- **`model_dump()`** gives a plain dict; **`model_dump_json()`** a compact JSON string, with `None` as `null`.
- **Assignment isn't validated by default.** The last line stored a string in an int field without complaint. Validation happens when the model is *created*; treat models as read-only after that, or opt in with `ConfigDict(validate_assignment=True)`.

**Connection to FastAPI:** a 422 body is these same errors with the source prepended to `loc`. Pydantic's `('username',)` appears in FastAPI as `["body", "username"]`.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "from pydantic import BaseModel\n\nclass Counter(BaseModel):\n    unread: int = 0\n\nc = Counter(unread=\"3\")\nc.unread = \"many\"\nprint(repr(c.unread))",
  "answer": "'many'",
  "explanation": "Creating the model converted \"3\" to 3. Plain assignment afterwards isn't validated (unless validate_assignment=True), so the string is stored as is." }
```

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "A Pydantic error has `loc` `('text',)`. The same model is used as the body of a FastAPI endpoint. What `loc` does the 422 response show?",
  "options": ["[\"text\"]", "[\"body\", \"text\"]", "[\"query\", \"text\"]", "[\"model\", \"text\"]"], "answer": 1,
  "explanation": "FastAPI prepends the source of the data. For a body model, that's \"body\"." }
```

## 6. Your turn: validate a chat export

Not every input comes through HTTP. The exercise validates rows from a chat export before import: keep the valid rows as models, and report each problem with its row number, field and error type, so a person can fix the file. No FastAPI needed.

```exercise
WEB.M02.L01.E1
```
