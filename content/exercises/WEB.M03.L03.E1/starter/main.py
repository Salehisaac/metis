# Finished: don't edit. Creates the app, includes your router, maps domain errors to HTTP.
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import folders_router
from services import FolderLimitReached, FolderNameTaken, FolderNotFound

app = FastAPI()
app.include_router(folders_router.router)

ERRORS = {
    FolderNotFound: (404, "folder not found"),
    FolderNameTaken: (409, "folder name already taken"),
    FolderLimitReached: (409, "folder limit reached"),
}


async def domain_error(request: Request, exc: Exception) -> JSONResponse:
    status, message = ERRORS[type(exc)]
    return JSONResponse(status_code=status, content={"detail": message})


for error_class in ERRORS:
    app.add_exception_handler(error_class, domain_error)
