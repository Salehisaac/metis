---
{
  "id": "WEB.M02.L02",
  "title": "Field constraints and custom validators",
  "difficulty": "intermediate",
  "minutes": 100,
  "prerequisites": ["WEB.M02.L01"],
  "objectives": [
    "Constrain fields with Field(min_length, max_length, pattern, ge, le, gt, lt) and reuse constraints with an Annotated alias",
    "Write a field_validator that normalises or rejects a value, and predict the error type and message it produces",
    "Choose mode=\"before\" when normalisation must happen before the built-in constraints",
    "Write a model_validator(mode=\"after\") for rules that involve several fields, and predict when it doesn't run"
  ],
  "why": "Types alone accept an empty username, a negative member count or a password confirmation that doesn't match. The rules that make data valid for your domain belong in the model too, so every endpoint, import and test that uses the model enforces them the same way, and the client gets them all in one 422.",
  "applications": [
    "Sign-up and profile forms: lengths, allowed characters, matching passwords",
    "Group settings with limits (2 to 200,000 members)",
    "Normalising input (trimming, lower-casing) once, at the boundary"
  ],
  "exercises": ["WEB.M02.L02.E1"],
  "sources": [
    {
      "title": "Pydantic API: pydantic.fields (Field parameters)",
      "url": "https://pydantic.dev/docs/validation/latest/api/pydantic/fields/",
      "version": "Pydantic docs 'latest' (page states no version; installed 2.14.2)",
      "verified": "2026-11-12",
      "claims": ["gt, ge, lt, le: greater/less than (or equal); only for numbers", "min_length and max_length: for iterables", "pattern: a regular expression for strings", "default_factory: a callable that generates the default"]
    },
    {
      "title": "Pydantic: Fields",
      "url": "https://pydantic.dev/docs/validation/latest/concepts/fields/",
      "version": "Pydantic docs 'latest' (page states no version; installed 2.14.2)",
      "verified": "2026-11-12",
      "claims": ["Field() behaves like the dataclasses field() function", "Field metadata can be attached with Annotated"]
    },
    {
      "title": "Pydantic: Validators",
      "url": "https://pydantic.dev/docs/validation/latest/concepts/validators/",
      "version": "Pydantic docs 'latest' (page states no version; installed 2.14.2)",
      "verified": "2026-11-12",
      "claims": ["@field_validator is applied on a class method", "After validators run after Pydantic's internal validation; before validators run before internal parsing and validation", "ValueError is the most common exception raised inside validators", "A model_validator in after mode must return the validated instance"]
    },
    {
      "title": "FastAPI Tutorial: Query Parameters and String Validations",
      "url": "https://fastapi.tiangolo.com/tutorial/query-params-str-validations/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Query() supports min_length, max_length and pattern", "Annotated is recommended"]
    }
  ]
}
---
## 1. Constraints with Field

With a Go validator library you'd write a struct tag such as `validate:"min=1,max=64"`, a string the compiler can't check. Pydantic uses `Field(...)` with keyword arguments:

```python
from typing import Annotated

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

Slug = Annotated[str, Field(min_length=3, max_length=32, pattern=r"^[a-z0-9-]+$")]


class CreateGroup(BaseModel):
    title: str = Field(min_length=1, max_length=64)
    slug: Slug
    max_members: int = Field(default=200, ge=2, le=200_000)


def show(model, **data):
    try:
        print(model(**data))
    except ValidationError as e:
        for err in e.errors():
            print(err["loc"], err["type"], "|", err["msg"])


show(CreateGroup, title="Go devs", slug="go-devs")
show(CreateGroup, title="", slug="Go Devs", max_members=1)
```

```console
title='Go devs' slug='go-devs' max_members=200
('title',) string_too_short | String should have at least 1 character
('slug',) string_pattern_mismatch | String should match pattern '^[a-z0-9-]+$'
('max_members',) greater_than_equal | Input should be greater than or equal to 2
```

- **Strings and lists:** `min_length`, `max_length`. **Strings:** `pattern` (a regex; anchor it with `^...$`, or it only has to match somewhere inside the value). **Numbers:** `ge`, `le` (≥, ≤), `gt`, `lt` (strict).
- `Field(default=200, ...)` sets a default *and* constraints. Without `default`, the field stays required.
- **`Slug = Annotated[str, Field(...)]`** is a reusable type: every model that says `slug: Slug` gets the same rules. It's the Pydantic version of a Go named type with a `Validate()` method, defined once.

These are the same constraint names you used on `Query(...)` in WEB.M01, and when the model is a FastAPI body, the same error types appear in the 422 with `loc` starting with `"body"`.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from pydantic import BaseModel, Field, ValidationError\n\nclass Mute(BaseModel):\n    minutes: int = Field(gt=0, le=1440)\n\nfor value in [1440, 0, 1441]:\n    try:\n        print(Mute(minutes=value).minutes)\n    except ValidationError as e:\n        print(e.errors()[0][\"type\"])",
  "answer": "1440\ngreater_than\nless_than_equal",
  "explanation": "le=1440 includes 1440. gt=0 is strict, so 0 fails with greater_than. 1441 is over the le limit." }
```

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "`code: str = Field(pattern=r\"[0-9]{6}\")` is meant to accept exactly six digits. Which input wrongly passes?",
  "options": ["\"123456\"", "\"abc1234567\"", "\"12345\"", "None of them; the pattern is correct"], "answer": 1,
  "explanation": "Without ^ and $, the regex only has to match somewhere in the string, and \"abc1234567\" contains six digits in a row. Use r\"^[0-9]{6}$\"." }
```

## 2. field_validator: your own rule for one field

For rules that a constraint can't express, write a **validator**: a class method decorated with `@field_validator("field_name")`. It receives the value; it returns the value to store (possibly changed), or raises `ValueError` to reject it.

By default a field validator runs **after** Pydantic's own validation (type conversion *and* `Field` constraints). That order has a trap:

```python
class CreateGroup(BaseModel):
    title: str = Field(min_length=1, max_length=64)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()


print(repr(CreateGroup(title="  Go devs  ").title))
print(repr(CreateGroup(title="   ").title))
```

```console
'Go devs'
''
```

`"   "` has length 3, so it passed `min_length=1`. *Then* the validator stripped it to `""`. You've stored an empty title despite the constraint.

## 3. mode="before": normalise first, then check

A **before** validator runs before Pydantic parses the value, so it sees the raw input (which may not even be a string yet). Normalise there, and the constraints check the normalised value:

```python
class CreateGroup(BaseModel):
    title: str = Field(min_length=1, max_length=64)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("title")
    @classmethod
    def no_shouting(cls, value: str) -> str:
        if value.isupper():
            raise ValueError("title must not be all caps")
        return value


for raw in ["  Go devs  ", "   ", "GO DEVS", 42]:
    try:
        print(repr(CreateGroup(title=raw).title))
    except ValidationError as e:
        print([(err["type"], err["msg"]) for err in e.errors()])
```

```console
'Go devs'
[('string_too_short', 'String should have at least 1 character')]
[('value_error', 'Value error, title must not be all caps')]
[('string_type', 'Input should be a valid string')]
```

What happened in each case:

- **The before validator guards with `isinstance`.** It gets raw input, so `42` arrives as an int. Calling `.strip()` on it would raise `AttributeError`, which is *not* turned into a validation error. Returning non-strings unchanged lets the normal `string_type` error happen.
- **A `ValueError` becomes an error of type `value_error`**, with your text after `"Value error, "` in `msg`. That's what the client sees in a 422.
- **The after validator** (`no_shouting`) can trust that `value` is a non-empty, stripped `str`.

For plain trimming there's also a model-wide switch, `model_config = ConfigDict(str_strip_whitespace=True)`, which strips every `str` field before the length checks. A validator is for when you need more than that.

**Common mistake: forgetting `return`.** A validator's return value *replaces* the field. Without a `return`, the function returns `None`, and that's what gets stored:

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "from pydantic import BaseModel, field_validator\n\nclass Invite(BaseModel):\n    max_uses: int\n\n    @field_validator(\"max_uses\")\n    @classmethod\n    def check_positive(cls, value: int) -> int:\n        if value <= 0:\n            raise ValueError(\"must be positive\")\n\nprint(Invite(max_uses=5).max_uses)",
  "answer": "None",
  "explanation": "The validator accepts 5 but never returns it, so it returns None, and None replaces the value. No error is raised. Always end a validator with return value." }
```

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "from pydantic import BaseModel, Field, ValidationError, field_validator\n\nclass Handle(BaseModel):\n    name: str = Field(max_length=5)\n\n    @field_validator(\"name\")\n    @classmethod\n    def lower(cls, value: str) -> str:\n        return value.strip().lower()\n\nfor raw in [\"  ALI  \", \"Ali\"]:\n    try:\n        print(Handle(name=raw).name)\n    except ValidationError as e:\n        print(e.errors()[0][\"type\"])",
  "answer": "string_too_long\nali",
  "explanation": "The validator runs after the constraints. \"  ALI  \" is 7 characters, so max_length=5 rejects it before the strip ever happens. \"Ali\" passes and is lower-cased. Making the validator mode=\"before\" would accept the first one as \"ali\"." }
```

## 4. model_validator: rules across fields

Some rules involve two fields: a range whose ends must differ, a password and its confirmation. A field validator only sees one field. A **model validator in after mode** runs once the whole model is built, gets `self`, and **must return `self`**:

```python
class QuietHours(BaseModel):
    start_hour: int
    end_hour: int

    @model_validator(mode="after")
    def check_range(self):
        if self.start_hour == self.end_hour:
            raise ValueError("start_hour and end_hour must differ")
        return self


print(QuietHours(start_hour=22, end_hour=7))
try:
    QuietHours(start_hour=8, end_hour=8)
except ValidationError as e:
    print([(err["loc"], err["type"], err["msg"]) for err in e.errors()])
try:
    QuietHours(start_hour="x", end_hour=8)
except ValidationError as e:
    print([(err["loc"], err["type"]) for err in e.errors()])
```

```console
start_hour=22 end_hour=7
[((), 'value_error', 'Value error, start_hour and end_hour must differ')]
[(('start_hour',), 'int_parsing')]
```

Two things to notice:

- **`loc` is empty `()`.** The error belongs to the model, not to a field. As a FastAPI body, it appears as `"loc": ["body"]`. If the client needs to highlight a field, say which one in the message (or, in WEB.M02.L04, in your own error format).
- **The model validator didn't run in the third case.** A field failed (`int_parsing`), so there was no complete model to give it. A client fixing that error might then get the range error on the next request. That's normal, and the reason cross-field errors should still be clear on their own.

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "If one field fails its own validation, a model_validator(mode=\"after\") still runs, so the client gets the field error and the cross-field error together.",
  "answer": false,
  "explanation": "An after model validator needs a fully built model. When a field fails, there is no model, so only the field errors are reported." }
```

```quiz
{ "id": "q6", "type": "choice", "label": "Application",
  "prompt": "Where should the rule \"`ends_at` must be later than `starts_at`\" for a scheduled message live?",
  "options": ["In every endpoint that accepts the schedule", "A field_validator on ends_at, reading starts_at from a global", "A model_validator(mode=\"after\") on the schedule model", "A Field(gt=...) constraint on ends_at"], "answer": 2,
  "explanation": "It involves two fields, so it belongs in a model validator, defined once and enforced wherever the model is used. Field(gt=...) only takes a fixed number, not another field." }
```

## 5. Your turn: a sign-up request

The exercise is the body model for `POST /signup` in the messaging app: a username that's normalised before it's checked, a display name, a password rule and a matching confirmation. Read the edge cases: which rules must run *before* the built-in checks, and which *after*?

```exercise
WEB.M02.L02.E1
```
