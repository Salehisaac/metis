"""Users API on SQLAlchemy. It works for a while in production, then every request fails.

Fix the session handling: one session per request, always closed.
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Engine, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=30)


class UserOut(BaseModel):
    id: int
    username: str


def get_session(request: Request) -> Session:
    return request.app.state.session


SessionDep = Annotated[Session, Depends(get_session)]


def create_app(engine: Engine) -> FastAPI:
    app = FastAPI()
    app.state.session = Session(engine)  # opened once, shared by every request

    @app.post("/users", status_code=201)
    def create_user(body: UserIn, session: SessionDep) -> UserOut:
        user = User(username=body.username)
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            raise HTTPException(status_code=409, detail="username taken")
        return UserOut(id=user.id, username=user.username)

    @app.get("/users")
    def list_users(session: SessionDep) -> list[UserOut]:
        users = session.scalars(select(User).order_by(User.id))
        return [UserOut(id=u.id, username=u.username) for u in users]

    return app
