from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Codes for HTTPException statuses; any other status gets "http_error".
STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
}


class AppError(Exception):
    """A domain rule was broken. Raised by the app; turned into a response by a handler."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def install_error_handlers(app: FastAPI) -> None:
    """Register the handlers that give every error the format in exercise.json."""
    # TODO
