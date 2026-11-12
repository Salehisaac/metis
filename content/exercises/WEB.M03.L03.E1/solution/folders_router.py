# HTTP layer for chat folders.
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from deps import get_folder_service
from services import FolderService

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
