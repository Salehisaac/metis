from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SignupRequest(BaseModel):
    """Body of POST /signup. TODO: add the rules from exercise.json."""

    username: str
    display_name: str
    password: str
    password_confirm: str
