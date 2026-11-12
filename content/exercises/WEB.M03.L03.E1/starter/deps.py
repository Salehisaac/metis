# Wiring: the app's "ServiceContext".
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from repository import FolderRepository
from services import FolderService


def get_repository() -> FolderRepository:
    """One shared FolderRepository for the whole process."""
    raise NotImplementedError  # TODO


def get_folder_service():
    """A FolderService around the repository from get_repository."""
    raise NotImplementedError  # TODO
