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


def error_response(status: int, code: str, message: str, headers=None, **extra) -> JSONResponse:
    body = {"error": {"code": code, "message": message, **extra}}
    return JSONResponse(status_code=status, content=body, headers=headers)


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status, exc.code, exc.message)


async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = STATUS_CODES.get(exc.status_code, "http_error")
    return error_response(exc.status_code, code, str(exc.detail), headers=exc.headers)


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(err["type"] == "json_invalid" for err in errors):
        return error_response(400, "malformed_json", "request body is not valid JSON")
    fields = [
        {"loc": ".".join(str(part) for part in err["loc"]), "type": err["type"], "message": err["msg"]}
        for err in errors
    ]
    return error_response(422, "validation_failed", "request validation failed", fields=fields)


def install_error_handlers(app: FastAPI) -> None:
    """Register the handlers that give every error the format in exercise.json."""
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
