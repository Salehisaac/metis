import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class Settings(BaseModel):
    page_size_default: int = 20
    page_size_max: int = 100
    read_only: bool = False


# Environment variable -> Settings field
ENV_VARS = {
    "FEED_PAGE_SIZE_DEFAULT": "page_size_default",
    "FEED_PAGE_SIZE_MAX": "page_size_max",
    "FEED_READ_ONLY": "read_only",
}


@lru_cache
def get_settings() -> Settings:
    """Build Settings from the environment variables that are set; the rest keep their defaults. Built once."""
    raw = {field: os.environ[var] for var, field in ENV_VARS.items() if var in os.environ}
    return Settings.model_validate(raw)


def page_size(settings: Annotated[Settings, Depends(get_settings)], limit: int | None = None) -> int:
    """The page size for this request: the query parameter `limit`, checked against the settings."""
    if limit is None:
        return settings.page_size_default
    if not 1 <= limit <= settings.page_size_max:
        raise HTTPException(status_code=422, detail=f"limit must be between 1 and {settings.page_size_max}")
    return limit


def require_writable(settings: Annotated[Settings, Depends(get_settings)]) -> None:
    """Stop the request with 503 while the feed is read-only."""
    if settings.read_only:
        raise HTTPException(status_code=503, detail="feed is read-only")


# ---- The routes are finished; they use your dependencies. ----

class NewPost(BaseModel):
    text: str


POSTS = [{"id": i, "text": f"post {i}"} for i in range(1, 251)]  # oldest first


@app.get("/feed")
def read_feed(limit: Annotated[int, Depends(page_size)]):
    newest_first = POSTS[::-1]
    return {"limit": limit, "items": newest_first[:limit]}


@app.post("/feed", status_code=201, dependencies=[Depends(require_writable)])
def create_post(body: NewPost):
    post = {"id": len(POSTS) + 1, "text": body.text}
    POSTS.append(post)
    return post
