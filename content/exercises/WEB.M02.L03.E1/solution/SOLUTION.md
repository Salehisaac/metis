```python
class UserCreate(BaseModel):          # what the client may send on sign-up
    username: str
    email: str
    password: str
    display_name: str
    bio: str | None = None


class UserPublic(BaseModel):          # what any client may see
    id: int
    username: str
    display_name: str
    bio: str | None = None


class UserPatch(BaseModel):           # what the client may change
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1)
    bio: str | None = None

    @field_validator("display_name")
    @classmethod
    def display_name_required_if_sent(cls, name):
        if name is None:
            raise ValueError("display_name cannot be null")
        return name


@app.post("/users", status_code=201, response_model=UserPublic)
def create_user(body: UserCreate): ...          # body unchanged


@app.get("/users/{user_id}", response_model=UserPublic)
def read_user(user_id: int): ...                # body unchanged


@app.patch("/users/{user_id}", response_model=UserPublic)
def edit_user(user_id: int, body: UserPatch):
    if user_id not in users:
        raise HTTPException(status_code=404, detail="user not found")
    users[user_id].update(body.model_dump(exclude_unset=True))
    return users[user_id]
```

**Why it works**

- **One model per direction.** `UserCreate` is the only model with `password`; `UserPublic` is an allowlist of four fields, so `email`, `password_hash`, `is_admin` and any field added to storage later never leave the server. `response_model` is used rather than `-> UserPublic` because the functions return dicts.
- **`exclude_unset=True` makes PATCH partial.** Only the keys the client sent are applied. An explicit `"bio": null` counts as sent, so it clears the bio; `{}` changes nothing.
- **Optional is not nullable.** `display_name` may be absent from a PATCH, but if it's sent it must be a non-empty string. `min_length=1` rejects `""`; the validator rejects an explicit `null` (it never runs for an absent field, because defaults aren't validated). Without it, `{"display_name": null}` would store `None`, and every later response would be a 500 from `UserPublic`.
- **`extra="forbid"` closes mass assignment.** `is_admin`, `username` and `password_hash` aren't fields of `UserPatch`, so sending them is a 422, not a silent no-op, and certainly not a write.
- **The docs follow the code.** With `response_model`, `/openapi.json` shows `UserPublic` as the 200 response, so the mobile team sees exactly the four fields.

**Alternatives**

- `GET /users/me` could return a `UserPrivate` model that adds `email`, so owners see their own email but nobody else's. That needs the current user, a dependency (WEB.M03).
- The lesson's model validator (checking `model_fields_set`) also blocks the null, but its error has `loc` `()`, shown by FastAPI as `["body"]`, so `test_patch_rejects_null_or_empty_display_name` fails. A field validator attaches the error to `display_name`, and because defaults aren't validated it never fires for an absent field.
- The edit-model trick for "optional but not nullable" can also be written with `Field(default=None)` on a plain `str` field, since defaults aren't validated. It works, but type checkers flag the `None` default, so the validator version is clearer.
- A real API would validate `email` with Pydantic's `EmailStr`, which needs the `email-validator` package (not installed here).
