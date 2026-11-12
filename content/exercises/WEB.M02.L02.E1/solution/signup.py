from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SignupRequest(BaseModel):
    """Body of POST /signup."""

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
