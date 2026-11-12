```python
class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    incoming = request.headers.get("X-Request-ID", "")
    rid = incoming if VALID_ID.match(incoming) else uuid.uuid4().hex
    request_id_var.set(rid)
    resp = await call_next(request)
    resp.headers["X-Request-ID"] = rid
    return resp


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    rid = request_id_var.get()
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": rid},
        headers={"X-Request-ID": rid},
    )
```

**Why it works**

- **One ID per request, in a ContextVar.** The middleware runs first for every request, picks the ID and sets `request_id_var`. Code running for that request (the endpoint, the filter, the error handler) reads the same value, and concurrent requests don't see each other's IDs. The logging cookbook recommends `contextvars` for exactly this, because it works for both threads and asyncio.
- **Validate incoming IDs.** Reusing an upstream ID (from a gateway or another service) lets you follow one request across services, but the header is client input: the regex keeps spaces, newlines and huge values out of your logs.
- **The filter** adds `request_id` to every record logged through `log`, so a JSON formatter (L02) emits it as a field without every call passing `extra=`.
- **The handler** is registered for `Exception`, so it sees only errors nothing else handled; `HTTPException` still goes to FastAPI's own handler and the 404 is unchanged. `log.exception` logs at ERROR with the traceback (it must be called while handling an exception, which a handler is).
- **The header is set in the handler.** Starlette sends responses for unhandled errors from its outermost layer (`ServerErrorMiddleware`), outside `@app.middleware("http")`, so the middleware's `resp.headers[...]` line never runs for them. In this lesson's run, the 500 came back without the header until the handler added it.
- **Generic body.** The client gets the request ID to quote in a bug report; the details (here a leaked-looking key in the exception message) stay in your logs.

**Alternative**

- Also store the ID on `request.state` if endpoints need it explicitly. The ContextVar is still what the logging filter can reach, since a filter never sees the request object.
