# Business rules for chat folders. No HTTP imports in this file.
from repository import FolderRepository


class FolderNotFound(Exception):
    pass


class FolderNameTaken(Exception):
    pass


class FolderLimitReached(Exception):
    pass


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
