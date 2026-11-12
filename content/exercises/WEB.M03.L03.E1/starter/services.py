# Business rules for chat folders. No FastAPI imports in this file.
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
        raise NotImplementedError  # TODO

    def get(self, folder_id: int) -> dict:
        raise NotImplementedError  # TODO

    def list(self) -> list[dict]:
        raise NotImplementedError  # TODO

    def delete(self, folder_id: int) -> None:
        raise NotImplementedError  # TODO
