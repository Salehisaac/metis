# HTTP layer for chat folders.
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from deps import get_folder_service
from services import FolderService

router = APIRouter()  # TODO: prefix and tags

# TODO: the four endpoints from exercise.json
