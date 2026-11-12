```python
@lru_cache
def get_settings() -> Settings:
    raw = {field: os.environ[var] for var, field in ENV_VARS.items() if var in os.environ}
    return Settings.model_validate(raw)


def page_size(settings: Annotated[Settings, Depends(get_settings)], limit: int | None = None) -> int:
    if limit is None:
        return settings.page_size_default
    if not 1 <= limit <= settings.page_size_max:
        raise HTTPException(status_code=422, detail=f"limit must be between 1 and {settings.page_size_max}")
    return limit


def require_writable(settings: Annotated[Settings, Depends(get_settings)]) -> None:
    if settings.read_only:
        raise HTTPException(status_code=503, detail="feed is read-only")
```

**Why it works**

- **`get_settings` passes only the variables that are set**, so missing ones fall back to the model's defaults. `model_validate` converts `"50"` to 50 and `"true"` to `True`, and an invalid value such as `"lots"` raises `ValidationError` at the first call: broken configuration fails loudly instead of halfway through a request. `@lru_cache` builds the object once; `cache_clear()` forces a rebuild.
- **`page_size` is a sub-dependency user.** It depends on `get_settings` *and* takes the `limit` query parameter. A fixed `Query(le=100)` can't follow configuration, so the bound is checked in code, with 422 to match FastAPI's own validation status. `int | None = None` separates "not sent" (use the default) from a real value; `if not limit:` would wrongly treat `0` as "not sent".
- **`require_writable` returns nothing**, so it's listed in the decorator's `dependencies=[...]`. It runs before the route body; raising 503 means `create_post` never runs and nothing is stored.
- **Overrides reach sub-dependencies.** The tests override only `get_settings`, and both `page_size` and `require_writable` see the test settings, because FastAPI swaps the dependency wherever it appears in the tree.

**Alternatives**

- 400 for an out-of-range limit is also defensible. 422 keeps it consistent with FastAPI's own `Query` validation, which clients already see for `limit=ten`.
- Clamping (`min(limit, max)`) instead of rejecting is friendlier for some clients, but it hides mistakes; whichever you pick, document it.
- `pydantic-settings`' `BaseSettings` (used in the FastAPI docs) reads the environment for you, including prefixes like `FEED_`. It isn't installed here; the explicit dict does the same job for three variables.
- 503 is "temporarily unable to handle the request"; a `Retry-After` header would tell clients when to try again.
