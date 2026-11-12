import hashlib
import itertools

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

app = FastAPI()


def fake_hash(password: str) -> str:
    """Stand-in for real password hashing (WEB.M06). Never store plain passwords."""
    return hashlib.sha256(password.encode()).hexdigest()


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    display_name: str
    bio: str | None = None


class UserPublic(BaseModel):
    id: int
    username: str
    display_name: str
    bio: str | None = None


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1)
    bio: str | None = None

    @field_validator("display_name")
    @classmethod
    def display_name_required_if_sent(cls, name):
        if name is None:
            raise ValueError("display_name cannot be null")
        return name


# Stored records also hold password_hash and is_admin. The database arrives in WEB.M05.
users: dict[int, dict] = {}
_ids = itertools.count(1)


@app.post("/users", status_code=201, response_model=UserPublic)
def create_user(body: UserCreate):
    user = {
        "id": next(_ids),
        "username": body.username,
        "email": body.email,
        "password_hash": fake_hash(body.password),
        "display_name": body.display_name,
        "bio": body.bio,
        "is_admin": False,
    }
    users[user["id"]] = user
    return user


@app.get("/users/{user_id}", response_model=UserPublic)
def read_user(user_id: int):
    if user_id not in users:
        raise HTTPException(status_code=404, detail="user not found")
    return users[user_id]


@app.patch("/users/{user_id}", response_model=UserPublic)
def edit_user(user_id: int, body: UserPatch):
    if user_id not in users:
        raise HTTPException(status_code=404, detail="user not found")
    users[user_id].update(body.model_dump(exclude_unset=True))
    return users[user_id]
