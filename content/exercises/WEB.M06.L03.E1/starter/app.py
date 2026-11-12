"""Login and current user for the chat API. Implement login() and get_current_user()."""

from dataclasses import dataclass
from typing import Annotated

import jwt  # noqa: F401  (you'll need it in get_current_user)
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from security import (  # noqa: F401  (all four are for your code)
    DUMMY_HASH,
    create_access_token,
    decode_access_token,
    verify_password,
)


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    disabled: bool = False


class Token(BaseModel):
    access_token: str
    token_type: str


class UserOut(BaseModel):
    id: int
    username: str


# Reads "Authorization: Bearer <token>"; answers 401 by itself when the header is missing.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def credentials_error() -> HTTPException:
    return HTTPException(status_code=401, detail="Could not validate credentials",
                         headers={"WWW-Authenticate": "Bearer"})


def find_user_by_id(users: dict[str, User], user_id: int) -> User | None:
    return next((u for u in users.values() if u.id == user_id), None)


def get_current_user(request: Request, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """The user the token belongs to.

    Any invalid token (bad signature, expired, wrong audience, sub that isn't a user id)
    and a user that no longer exists all raise credentials_error().
    """
    raise NotImplementedError


def get_current_active_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


def create_app(users: dict[str, User]) -> FastAPI:
    """users maps username -> User."""
    app = FastAPI()
    app.state.users = users

    @app.post("/auth/token")
    def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
        """Return {"access_token": ..., "token_type": "bearer"} for correct credentials.

        The credentials arrive as form fields (form.username, form.password), as the OAuth2
        password flow requires.

        Unknown username and wrong password both answer 400 "Incorrect username or password",
        and both run exactly one password check (verify_password against DUMMY_HASH for an
        unknown user), so the response time doesn't reveal which usernames exist.
        """
        raise NotImplementedError

    @app.get("/users/me")
    def read_me(user: Annotated[User, Depends(get_current_active_user)]) -> UserOut:
        return UserOut(id=user.id, username=user.username)

    return app
