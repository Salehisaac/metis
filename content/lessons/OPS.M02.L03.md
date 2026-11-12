---
{
  "id": "OPS.M02.L03",
  "title": "Error reporting in FastAPI: request IDs and exception handlers",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["OPS.M02.L02"],
  "objectives": [
    "Give every request an ID in middleware, store it in a ContextVar and return it as a response header",
    "Attach the request ID to log records with a logging.Filter, and choose between a logger filter and a handler filter",
    "Register an exception handler for unhandled errors that logs the traceback with context and returns a generic 500",
    "Explain why a response for an unhandled exception bypasses @app.middleware, and handle it"
  ],
  "why": "A user reports 'I got an error at 14:02'. Without a request ID you scroll through thousands of lines guessing which traceback is theirs, and if the 500 body contains the exception message you may also have shown them an internal hostname or a key. A request ID in every log line, in the response header and in the error body turns that into one search.",
  "applications": [
    "Support asks for the request ID shown in an error message and finds the exact traceback",
    "Following one request across services by passing X-Request-ID along",
    "Error responses that are safe to show to clients"
  ],
  "exercises": ["OPS.M02.L03.E1"],
  "sources": [
    {
      "title": "FastAPI: Middleware",
      "url": "https://fastapi.tiangolo.com/tutorial/middleware/",
      "version": "FastAPI docs (current; installed fastapi 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["@app.middleware(\"http\") functions receive the request and call_next; call_next(request) returns the response, which you can modify before returning", "Custom headers can use the X- prefix"]
    },
    {
      "title": "FastAPI: Handling Errors",
      "url": "https://fastapi.tiangolo.com/tutorial/handling-errors/",
      "version": "FastAPI docs (current; installed fastapi 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["@app.exception_handler(SomeException) installs a handler that receives the request and the exception and returns a response", "FastAPI's HTTPException inherits from Starlette's; default handlers produce the JSON for HTTPException and RequestValidationError"]
    },
    {
      "title": "Starlette: Exceptions",
      "url": "https://starlette.dev/exceptions/",
      "version": "Starlette docs (current; installed starlette 1.10.0)",
      "verified": "2026-11-12",
      "claims": ["Errors (anything not handled) bubble through the middleware stack; ServerErrorMiddleware is the outermost layer and returns the 500", "exception_handlers can use the key Exception or 500", "HTTPException is a handled exception turned into a normal response"]
    },
    {
      "title": "contextvars: Context Variables",
      "url": "https://docs.python.org/3.12/library/contextvars.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["ContextVar(name, default=...); get() returns the default when unset; set() returns a Token", "Context variables should be created at module level", "Context variables are natively supported in asyncio"]
    },
    {
      "title": "logging: Filter objects, Logger.exception, exc_info",
      "url": "https://docs.python.org/3.12/library/logging.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Handler filters are consulted before the handler emits; logger filters only for events logged on that logger, not on descendants", "Logger.exception logs at ERROR with exception info and should only be called from an exception handler", "exc_info accepts an exception instance (since 3.5)"]
    },
    {
      "title": "Logging Cookbook: contextual information and contextvars",
      "url": "https://docs.python.org/3.12/howto/logging-cookbook.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["A Filter can add contextual attributes to LogRecords for use in format strings", "contextvars provide context-local storage for both threading and asyncio and may be preferable to thread-locals; example injects request data via a Filter"]
    }
  ]
}
---
## 1. What a good error report contains

When a request fails in production, you want three things in your logs and one thing in the response:

| Logs (for you) | Response (for the client) |
|---|---|
| **which request** failed: a request ID, method, path | a generic message |
| **what** happened: the full traceback | the request ID, so they can quote it |
| **context**: user or order id, never secrets | nothing internal: no exception text, no hostnames |

This lesson builds that with three stdlib and FastAPI pieces: a ContextVar, a logging Filter and an exception handler. If you've seen trace IDs in Go services' logs, this is the same idea, done by hand.

## 2. ContextVar: a per-request global

The request ID has to be readable from places that never see the `request` object, such as a logging filter or a function three calls deep. A module-level variable would be shared by all concurrent requests. A **`ContextVar`** is the safe version: each request's code sees its own value. The logging cookbook recommends it over thread-locals because it works for both threads and asyncio.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "Two 'requests' run concurrently and each sets the same ContextVar. What does this print?",
  "code": "import asyncio\nfrom contextvars import ContextVar\n\ncurrent = ContextVar(\"current\", default=\"-\")\n\n\nasync def handle(name):\n    current.set(name)\n    await asyncio.sleep(0)\n    return current.get()\n\n\nasync def main():\n    print(await asyncio.gather(handle(\"a\"), handle(\"b\")))\n    print(current.get())\n\n\nasyncio.run(main())",
  "answer": "['a', 'b']\n-",
  "explanation": "gather runs each coroutine as a task with its own copy of the context, so 'b' setting the variable doesn't overwrite 'a', even though both pause at the sleep. main's own context was never set, so it still sees the default." }
```

Create ContextVars **at module level**, as the docs require, and always give one a default, so code outside a request (startup, tests) gets `"-"` instead of a `LookupError`.

## 3. Middleware sets the ID, a Filter puts it on every record

Here is an inventory service (not the exercise's app) that tags each request with a short correlation ID. The pieces:

- **Middleware** runs around every request. FastAPI passes it the `request` and `call_next`; `await call_next(request)` runs the endpoint and returns the response, which you can still modify.
- A **logging Filter** that *adds* an attribute to each record and returns True, so nothing is dropped. The cookbook calls this "imparting contextual information".

```python
import logging
import sys
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

correlation = ContextVar("correlation", default="-")
logger = logging.getLogger("inventory")


class CorrelationFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = correlation.get()
        return True


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(levelname)s [%(correlation_id)s] %(message)s"))
handler.addFilter(CorrelationFilter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

api = FastAPI()


@api.middleware("http")
async def tag_request(request: Request, call_next):
    cid = uuid.uuid4().hex[:8]
    correlation.set(cid)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response


@api.exception_handler(Exception)
async def report(request: Request, exc: Exception):
    logger.error("unhandled %s on %s", type(exc).__name__, request.url.path, exc_info=exc)
    return JSONResponse({"error": "internal", "correlation_id": correlation.get()}, status_code=500)


@api.get("/stock/{sku}")
def stock(sku: str):
    if sku == "broken":
        raise RuntimeError("warehouse DB timeout")
    logger.info("stock lookup for %s", sku)
    return {"sku": sku, "count": 3}


client = TestClient(api, raise_server_exceptions=False)
r = client.get("/stock/abc")
print(r.status_code, r.headers.get("X-Correlation-ID"))
r = client.get("/stock/broken")
print(r.status_code, r.headers.get("X-Correlation-ID"), r.json())
```

Real output (IDs are random; the traceback is trimmed to its first and last lines):

```console
INFO [78163067] stock lookup for abc
200 78163067
ERROR [d5abcaea] unhandled RuntimeError on /stock/broken
Traceback (most recent call last):
  File ".../starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  ...
  File ".../inventory.py", line 47, in stock
    raise RuntimeError("warehouse DB timeout")
RuntimeError: warehouse DB timeout
500 None {'error': 'internal', 'correlation_id': 'd5abcaea'}
```

Notice:

- The sync endpoint `stock` runs in a worker thread, and it still saw the ID: FastAPI runs it inside the request's context.
- The **filter is on the handler** here, so it applies to every record that handler emits, including records from child loggers like `inventory.db`. A filter on a **logger** only runs for records logged on that exact logger, not its descendants. The exercise puts the filter on its one `app` logger, which is enough there.
- In production, the filter feeds the JSON formatter from L02: `correlation_id` becomes just another field.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "A filter that sets record.request_id is added with `logging.getLogger(\"app\").addFilter(...)`. A module logs with `logging.getLogger(\"app.payments\")`. Do its records get request_id?",
  "options": ["No: logger filters only run for records logged on that logger itself; put it on the handler instead", "Yes: filters propagate to child loggers", "Yes, but only at ERROR", "Only if propagate is False"], "answer": 0,
  "explanation": "Per the logging docs, events generated by descendant loggers aren't filtered by an ancestor logger's filters. A handler filter runs for every record that handler emits, wherever it came from." }
```

## 4. The exception handler, and the header that went missing

Look at the second request again: `500 None`. **The 500 response has no `X-Correlation-ID` header**, even though the middleware sets it on every response. Why?

- `HTTPException` is a *handled* exception: FastAPI turns it into a normal response inside the app, and it travels back through your middleware like any other response.
- Any other exception is an *error*. Per Starlette's docs, it bubbles out through the whole middleware stack, including through `await call_next(request)` in your middleware, so the line that sets the header never runs. The outermost layer, `ServerErrorMiddleware`, calls the handler registered for `Exception` and sends its response.

So a handler for unhandled errors must do everything itself: log, build the body and **set the header**. The ContextVar still holds the ID; the handler's own log line shows `[d5abcaea]`. The body uses it already. Only the header is missing.

What the handler should and shouldn't do:

- **Log with the traceback**: `logger.exception(...)` inside a handler, or `logger.error(..., exc_info=exc)` as above. Both log at ERROR with the traceback.
- **Identify the request**: method and path in the message, the request ID via the filter.
- **Return something generic**: never `str(exc)`. Exception messages contain SQL, hostnames, file paths and sometimes credentials.
- Register it for `Exception`, so `HTTPException` (404s, 403s) keeps FastAPI's normal handler and its usual `{"detail": ...}` body.

In tests, use `TestClient(app, raise_server_exceptions=False)`. By default TestClient re-raises the server's exception in your test, so you'd never see the 500 response.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "If a middleware adds a header with `response.headers[...] = ...` after `await call_next(request)`, every response gets the header, including 500s from unhandled exceptions.", "answer": false,
  "explanation": "An unhandled exception propagates out of call_next, so the rest of the middleware doesn't run. The 500 comes from ServerErrorMiddleware, outside your middleware; set the header in the exception handler." }
```

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "Which handler body is safe to return to clients for an unhandled exception?",
  "options": ["{\"detail\": \"Internal Server Error\", \"request_id\": rid}", "{\"detail\": str(exc)}", "{\"detail\": traceback.format_exc()}", "{\"detail\": repr(request.headers)}"], "answer": 0,
  "explanation": "The client only needs to know it failed and which ID to report. Exception text and tracebacks leak internals; request headers can contain the client's own Authorization token, which then lands in screenshots and tickets." }
```

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "Why should an incoming X-Request-ID header be validated before you reuse it?",
  "options": ["It's client input that goes into your logs and headers; reject anything that isn't a short, safe token", "Starlette rejects requests with unknown headers", "UUIDs must be generated by the server for the logs to sort", "Header values are always bytes"], "answer": 0,
  "explanation": "Reusing an upstream ID is useful for tracing across services, but a client can send anything: newlines that forge log lines, huge strings. A strict pattern plus a fallback to a fresh ID keeps logs trustworthy." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "A customer emails: 'Checkout failed with request ID 3f9c...'. Describe the path from that ID to the root cause, using what this lesson built.",
  "model": "Search the log system for request_id=3f9c... (every record from that request has the field via the filter). The ERROR record from the exception handler has method, path and the full traceback; INFO records around it show what the request did before failing. The customer never saw internals, only the ID.",
  "explanation": "The request ID connects the client-visible error to the server-side evidence." }
```

## 5. Your turn

Complete `app.py`: middleware that reuses a valid incoming `X-Request-ID` or generates one, a filter that copies it onto records, and an `Exception` handler that logs the traceback and returns a generic 500 with the request ID, in the body *and* in the header.

```exercise
OPS.M02.L03.E1
```
