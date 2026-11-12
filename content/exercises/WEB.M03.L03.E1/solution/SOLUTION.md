```python
# services.py (no HTTP imports)
class FolderService:
    def __init__(self, repo: FolderRepository, max_folders: int = 3):
        self.repo = repo
        self.max_folders = max_folders

    def create(self, name: str) -> dict:
        clean = name.strip()
        if not clean:
            raise ValueError("folder name must not be blank")
        existing = self.repo.all()
        if any(f["name"].casefold() == clean.casefold() for f in existing):
            raise FolderNameTaken(clean)
        if len(existing) >= self.max_folders:
            raise FolderLimitReached(self.max_folders)
        return self.repo.add(clean)

    def get(self, folder_id: int) -> dict:
        folder = self.repo.get(folder_id)
        if folder is None:
            raise FolderNotFound(folder_id)
        return folder

    def list(self) -> list[dict]:
        return sorted(self.repo.all(), key=lambda f: f["name"].casefold())

    def delete(self, folder_id: int) -> None:
        if not self.repo.remove(folder_id):
            raise FolderNotFound(folder_id)
```

```python
# deps.py
@lru_cache
def get_repository() -> FolderRepository:
    return FolderRepository()


def get_folder_service(repo: Annotated[FolderRepository, Depends(get_repository)]) -> FolderService:
    return FolderService(repo)
```

```python
# folders_router.py
router = APIRouter(prefix="/folders", tags=["folders"])

Folders = Annotated[FolderService, Depends(get_folder_service)]


class FolderIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=40)


class FolderOut(BaseModel):
    id: int
    name: str


@router.post("", status_code=201, response_model=FolderOut)
def create_folder(body: FolderIn, folders: Folders):
    return folders.create(body.name)


@router.get("", response_model=list[FolderOut])
def list_folders(folders: Folders):
    return folders.list()


@router.get("/{folder_id}", response_model=FolderOut)
def read_folder(folder_id: int, folders: Folders):
    return folders.get(folder_id)


@router.delete("/{folder_id}", status_code=204)
def delete_folder(folder_id: int, folders: Folders):
    folders.delete(folder_id)
```

**Why it works**

- **The service holds every rule** (strip, blank, case-insensitive uniqueness, the limit, not-found) and raises domain exceptions. It never mentions HTTP, so the service tests run with no client, and `main.py`'s handlers map each exception to a status in one place.
- **The order of checks in `create`**: a duplicate name is reported as a duplicate even when the limit is also reached, which is the more useful message. Deleting a folder frees a slot because the limit counts the current rows.
- **`get_repository` is cached**, so production requests share one store. `get_folder_service` builds a cheap service per request around it. The tests override only `get_repository`; the override reaches the service through the sub-dependency, and each test gets its own empty store.
- **The router stays thin**: validation of the body (strip, then `min_length=1`, so `"   "` is a 422 before the service is called), an output model, and one service call per endpoint. No `try/except`, because `main.py` registered handlers for the domain exceptions.
- The service *also* rejects blank names with `ValueError`. That's deliberate: other callers (an import script) don't go through the HTTP model.

**Alternatives**

- With the docs' package layout (`app/routers/folders.py`, `app/services.py`, `app/dependencies.py`) the code is identical except for relative imports (`from ..services import FolderService`).
- `max_folders` would normally come from settings: `get_folder_service(repo=..., settings=Depends(get_settings))` passes `settings.max_folders`. That's L01's pattern, one more sub-dependency.
- A per-user folder list needs the current user (L02) in `get_folder_service` or as a service method argument.
