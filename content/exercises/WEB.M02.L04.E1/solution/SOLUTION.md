```python
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
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
```

**Why it works**

- **One builder, one shape.** Every handler calls `error_response`, so the `{"error": {...}}` envelope is written once. `**extra` adds `fields` only for validation errors.
- **Starlette's `HTTPException`** catches your own `raise HTTPException(...)` *and* the router's 404 and 405, which FastAPI's subclass would miss.
- **`headers=exc.headers`** keeps `Allow` on the 405 (an RFC 9110 MUST) and `WWW-Authenticate` on the 401. Without it, the body is right and the headers are silently gone.
- **Validation details are rebuilt, not copied.** Only `loc`, `type` and `msg` are used. That avoids the `ValueError` object in a `value_error`'s `ctx` (which would crash `JSONResponse` with a `TypeError`) and never echoes `input`, which on other endpoints could be a password.
- **400 vs 422.** A body that isn't JSON at all arrives as a `RequestValidationError` with type `json_invalid`; that's malformed syntax, so it gets 400 per RFC 9110. Everything else is syntactically fine but invalid, so 422.

**Alternatives**

- `@app.exception_handler(...)` decorators inside `install_error_handlers` work the same; `app.add_exception_handler(cls, func)` is the plain-function form of the same registration, handy when the handlers live in their own module.
- A popular standard for this envelope is "problem details" (`application/problem+json`, RFC 9457). It's worth reading before you design a public API's format; the mechanics are exactly these handlers.
- In production you'd also log unexpected exceptions with a request id and return a generic 500 body in the same format. That's an `Exception` handler or middleware (OPS course).
