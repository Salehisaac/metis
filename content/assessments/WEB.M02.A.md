---
{ "id": "WEB.M02.A", "module": "WEB.M02", "title": "WEB.M02 module assessment: Pydantic validation, response models and error format", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before WEB.M03.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "from pydantic import BaseModel, Field, ValidationError\n\nclass Ban(BaseModel):\n    user_id: int\n    minutes: int = Field(ge=1, le=10080)\n\nb = Ban(user_id=\"5\", minutes=\"30\")\nprint(b.user_id + b.minutes)\ntry:\n    Ban(user_id=5.5, minutes=0)\nexcept ValidationError as exc:\n    print([e[\"type\"] for e in exc.errors()])",
  "answer": "35\n['int_from_float', 'greater_than_equal']",
  "explanation": "Numeric strings are converted, so 5 + 30 = 35. 5.5 can't become an int without loss, and 0 breaks ge=1; both errors are reported together." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "from pydantic import BaseModel, Field, field_validator\n\nclass Tag(BaseModel):\n    name: str = Field(min_length=2)\n\n    @field_validator(\"name\")\n    @classmethod\n    def clean(cls, value: str) -> str:\n        return value.strip()\n\nprint(repr(Tag(name=\"  \").name))",
  "answer": "''",
  "explanation": "The validator runs after the constraints: \"  \" has length 2, so min_length passes, and only then is it stripped to an empty string. Use mode=\"before\" to strip first." }
```

```quiz
{ "id": "a3", "type": "output",
  "prompt": "What does this print?",
  "code": "from pydantic import BaseModel\n\nclass ProfileEdit(BaseModel):\n    bio: str | None = None\n    city: str | None = None\n\nstored = {\"bio\": \"gopher\", \"city\": \"Tehran\"}\nstored.update(ProfileEdit.model_validate({\"bio\": None}).model_dump(exclude_unset=True))\nprint(stored)",
  "answer": "{'bio': None, 'city': 'Tehran'}",
  "explanation": "bio was explicitly set (to None), so it's included and clears the stored bio. city wasn't sent, so exclude_unset leaves it out and the stored value stays." }
```

```quiz
{ "id": "a4", "type": "choice",
  "prompt": "`@app.get(\"/users/{user_id}\", response_model=UserPublic)` returns the stored dict `{\"id\": 1, \"username\": \"sara\", \"password_hash\": \"...\"}`, and `UserPublic` declares `id`, `username` and `bio: str | None = None`. What does the client receive?",
  "options": ["The whole stored dict", "{\"id\": 1, \"username\": \"sara\", \"bio\": null}", "A 500, because bio is missing from the dict", "{\"id\": 1, \"username\": \"sara\"}"], "answer": 1,
  "explanation": "The response model filters to its declared fields (password_hash is dropped) and fills bio from its default. bio has a default, so its absence isn't an error." }
```

```quiz
{ "id": "a5", "type": "choice", "label": "Debugging",
  "prompt": "After installing a custom error format, a 405 response has the right JSON body but no `Allow` header. What's the most likely cause?",
  "options": ["FastAPI never sends Allow", "The HTTPException handler builds a JSONResponse without headers=exc.headers", "The handler is registered for RequestValidationError", "The route needs status_code=405"], "answer": 1,
  "explanation": "The Allow header travels on the exception. A handler that builds a new response must copy exc.headers, or the header is lost." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "A client sends `{\"title\": \"Team\"` (missing closing brace) to `POST /chats`. What does a default FastAPI app answer, what does RFC 9110 suggest, and what would you configure and why?",
  "model": "Default FastAPI: 422 with an error of type json_invalid. RFC 9110: 400 is for malformed request syntax; 422 is for content whose syntax is correct but which can't be processed. I'd map json_invalid to 400 in a RequestValidationError handler (and keep 422 for invalid values), using the same error envelope, and document it. Keeping 422 everywhere is also defensible if it's consistent and documented.",
  "explanation": "Know the default, know the RFC, choose deliberately and document it." }
```
