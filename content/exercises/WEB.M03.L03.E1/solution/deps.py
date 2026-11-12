# Wiring: the app's "ServiceContext".
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from repository import FolderRepository
from services import FolderService


@lru_cache
def get_repository() -> FolderRepository:
    """One shared FolderRepository for the whole process."""
    return FolderRepository()


def get_folder_service(repo: Annotated[FolderRepository, Depends(get_repository)]) -> FolderService:
    """A FolderService around the repository from get_repository."""
    return FolderService(repo)
