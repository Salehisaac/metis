```python
class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=20, pattern=r"^[a-z0-9_]+$")
    display_name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8, max_length=64)
    password_confirm: str

    @field_validator("username", mode="before")
    @classmethod
    def normalise_username(cls, raw):
        if isinstance(raw, str):
            return raw.strip().lower()
        return raw

    @field_validator("display_name", mode="before")
    @classmethod
    def strip_display_name(cls, raw):
        if isinstance(raw, str):
            return raw.strip()
        return raw

    @field_validator("password")
    @classmethod
    def letter_and_digit(cls, password: str) -> str:
        has_letter = any(ch.isalpha() for ch in password)
        has_digit = any(ch.isdigit() for ch in password)
        if not (has_letter and has_digit):
            raise ValueError("password needs a letter and a digit")
        return password

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError("passwords do not match")
        return self
```

**Why it works**

- **Before validators for normalising.** `"  ab  "` must fail `min_length=3`, and `"ALI"` must pass a lower-case-only pattern. Both only work if strip and lower happen *before* the constraints, so they're `mode="before"`. The `isinstance` guard lets `123` fall through to the normal `string_type` error instead of crashing with `AttributeError`.
- **An after validator for the password rule.** By then `password` is a `str` that already passed the length limits, so the check only has to look for a letter and a digit. It returns the password unchanged: no stripping, since spaces are legal password characters.
- **A model validator for the confirmation.** It needs two fields. Because it runs only on a complete model, an invalid password produces just the password error, never a confusing "do not match" on top.
- **`[a-z0-9_]` rejects non-ASCII letters** like `علی`. `str.isalpha()` would accept them. Whether to allow them is a product decision; the pattern makes the decision explicit.

**Alternatives**

- `Annotated` aliases (`Username = Annotated[str, Field(...)]`) let a future `UpdateProfile` model reuse the same username rules.
- Don't put the full password policy in error messages that include the input. FastAPI's default 422 echoes `input`, including the password; WEB.M02.L04 shows how to leave it out.
- Real password strength checks (length plus a breached-password list) matter more than character classes; WEB.M06 covers hashing.
