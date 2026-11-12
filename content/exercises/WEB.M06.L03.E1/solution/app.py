"""Login and current user for the chat API."""

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from security import DUMMY_HASH, create_access_token, decode_access_token, verify_password


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
    try:
        user_id = int(decode_access_token(token)["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise credentials_error()
    user = find_user_by_id(request.app.state.users, user_id)
    if user is None:
        raise credentials_error()
    return user


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
        user = app.state.users.get(form.username)
        stored = user.password_hash if user is not None else DUMMY_HASH
        if not verify_password(form.password, stored) or user is None:
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        return Token(access_token=create_access_token(user.id), token_type="bearer")

    @app.get("/users/me")
    def read_me(user: Annotated[User, Depends(get_current_active_user)]) -> UserOut:
        return UserOut(id=user.id, username=user.username)

    return app
