---
{
  "id": "WEB.M02.L04",
  "title": "Consistent error responses: exception handlers, 422 vs 400",
  "difficulty": "intermediate",
  "minutes": 110,
  "prerequisites": ["WEB.M01", "WEB.M02.L03"],
  "objectives": [
    "Register exception handlers for a domain exception, for HTTPException and for RequestValidationError",
    "Explain why the HTTPException handler is registered for Starlette's class, and keep the exception's headers",
    "Build validation error bodies without crashing on non-JSON values and without echoing the input",
    "Argue 400 vs 422 for malformed JSON and for invalid values, using RFC 9110 and FastAPI's actual behaviour"
  ],
  "why": "Out of the box, a FastAPI client has to handle a string detail, a list detail and whatever your own errors look like. One error format means one parser on every client, one assertion helper in your tests, and no surprises from framework errors like 404 for an unknown route. It's also where you decide what an error may reveal: the default 422 echoes the input, password included.",
  "applications": [
    "A single error contract for mobile and web clients",
    "Domain rules (closed poll, blocked user) mapped to status codes in one place",
    "Not leaking request data in error responses"
  ],
  "exercises": ["WEB.M02.L04.E1"],
  "sources": [
    {
      "title": "FastAPI Tutorial: Handling Errors",
      "url": "https://fastapi.tiangolo.com/tutorial/handling-errors/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Custom exception handlers are added with @app.exception_handler(ExceptionClass)", "Invalid request data makes FastAPI raise RequestValidationError, which can be overridden", "Register the HTTPException handler for Starlette's HTTPException so Starlette's own errors are caught too", "FastAPI's HTTPException inherits from Starlette's; FastAPI's accepts any JSON-able detail, Starlette's only strings", "Converting the validation error to a string and returning it can leak information; extract each error instead", "Default handlers can be reused from fastapi.exception_handlers"]
    },
    {
      "title": "RFC 9110: HTTP Semantics (sections 15.5.1, 15.5.6, 15.5.21)",
      "url": "https://www.rfc-editor.org/rfc/rfc9110.html",
      "version": "RFC 9110 (June 2022, STD 97)",
      "verified": "2026-11-12",
      "claims": ["400: the server cannot or will not process the request due to a perceived client error, e.g. malformed request syntax", "422: the server understands the content type and the syntax of the content is correct, but it was unable to process the contained instructions", "A 405 response MUST include an Allow header"]
    },
    {
      "title": "FastAPI Tutorial: Query Parameters",
      "url": "https://fastapi.tiangolo.com/tutorial/query-params/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["FastAPI answers invalid input with 422 and a detail list"]
    }
  ]
}
---
## 1. Pick one format

In WEB.M01.L03 you saw that a default FastAPI app sends `{"detail": "..."}` for some errors and `{"detail": [...]}` for others. Here's the goal: **every** error response, whoever raised it, has the same top-level keys. In this lesson's example API (polls in a group chat) the format is:

```json
{"code": "poll_closed", "message": "this poll no longer accepts votes"}
```

with an extra `errors` list for validation failures. `code` is for programs (stable, snake_case), `message` for people. The exercise uses a slightly different, nested shape; a real team picks one and writes it down.

The tool is the **exception handler**: a function FastAPI calls when a given exception class escapes a path operation. It receives the request and the exception and returns a response. In Go terms, it's the error-to-response mapping you'd otherwise write in a middleware or in a `writeError(w, err)` helper called from every handler, except the framework calls it for you.

## 2. Domain exceptions and their handler

Path operations shouldn't need to know the error format. They raise an exception that *describes the problem*, and one handler turns it into JSON:

```python
# polls_api.py
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()


class PollError(Exception):
    """A rule of the polls domain was broken."""

    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


@app.exception_handler(PollError)
async def poll_error_handler(request: Request, exc: PollError):
    return JSONResponse(status_code=exc.status, content={"code": exc.code, "message": exc.message})


closed_polls = {7}


@app.post("/polls/{poll_id}/votes", status_code=201)
def vote(poll_id: int, option: int):
    if poll_id in closed_polls:
        raise PollError(409, "poll_closed", "this poll no longer accepts votes")
    return {"poll_id": poll_id, "option": option}
```

```console
POST /polls/7/votes?option=1 -> 409 {'code': 'poll_closed', 'message': 'this poll no longer accepts votes'}
```

- Handlers are `async def` in the FastAPI docs, and here; the body doesn't await anything, which is fine. (What `async` actually does is the AS course.)
- `JSONResponse(status_code=..., content=...)` is a response you build yourself. FastAPI sends it as is: no response model, no filtering.
- Raising your own exception class keeps HTTP out of your business logic. In WEB.M03 that logic moves into a service module that doesn't import FastAPI at all.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI, Request\nfrom fastapi.responses import JSONResponse\nfrom fastapi.testclient import TestClient\n\nclass Blocked(Exception):\n    pass\n\napp = FastAPI()\n\n@app.exception_handler(Blocked)\nasync def blocked_handler(request: Request, exc: Blocked):\n    return JSONResponse(status_code=403, content={\"code\": \"blocked\", \"message\": str(exc)})\n\n@app.post(\"/users/{username}/messages\")\ndef send(username: str):\n    if username == \"omid\":\n        raise Blocked(\"omid blocked you\")\n    return {\"sent\": True}\n\nc = TestClient(app)\nprint(c.post(\"/users/sara/messages\").json())\nr = c.post(\"/users/omid/messages\")\nprint(r.status_code, r.json())",
  "answer": "{'sent': True}\n403 {'code': 'blocked', 'message': 'omid blocked you'}",
  "explanation": "The first request returns normally. The second raises Blocked, which escapes the path operation; FastAPI finds the handler registered for that class and sends its JSONResponse." }
```

## 3. Replace the HTTPException handler, and keep its headers

Your own `raise HTTPException(...)` calls, and FastAPI's "Not Found" and "Method Not Allowed", all go through one handler. Override it so they use your format. The docs give one important rule: **register it for Starlette's `HTTPException`**, not FastAPI's. FastAPI's class inherits from Starlette's, and the router's own 404 and 405 are raised as *Starlette* exceptions. A handler for FastAPI's class would miss them.

```python
@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": f"http_{exc.status_code}", "message": str(exc.detail)},
        headers=exc.headers,
    )
```

The request is written on the left; the script printed status, body and the `allow` header (shown as `allow:`):

```console
GET /pols -> 404 {'code': 'http_404', 'message': 'Not Found'}
DELETE /polls -> 405 {'code': 'http_405', 'message': 'Method Not Allowed'} allow: POST
```

**Don't forget `headers=exc.headers`.** The 405 exception carries the `Allow` header, which RFC 9110 says a 405 response MUST include (and later, a 401 carries `WWW-Authenticate`). The same handler without that line, run against the same request:

```console
405 {'code': 'http_405', 'message': 'Method Not Allowed'} allow: None
```

The body looks perfect, and the header is silently gone. Only a test that checks the header notices.

`str(exc.detail)` makes the message a string even when someone raised `HTTPException(detail={...})`. Mapping status codes to nicer codes (`404` → `"not_found"`) is a small dict lookup; the exercise asks for it.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "You register a handler with `@app.exception_handler(fastapi.HTTPException)`. Which responses still come out in FastAPI's default `{\"detail\": ...}` format?",
  "options": ["None; all HTTP errors use the handler", "The router's own 404 for unknown paths and 405 for wrong methods", "Only your own raise HTTPException(...) calls", "Only 422 validation errors"], "answer": 1,
  "explanation": "The router raises Starlette's HTTPException, the parent class, which a handler for the FastAPI subclass doesn't catch. That's why the docs say to register Starlette's class. (422s go to the RequestValidationError handler either way.)" }
```

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "A custom HTTPException handler that returns `JSONResponse(status_code=exc.status_code, content={...})` still sends the Allow header on a 405, because FastAPI adds it after the handler runs.",
  "answer": false,
  "explanation": "The header lives on the exception (exc.headers). If the handler doesn't pass headers=exc.headers, the response has no Allow header, as the run above shows." }
```

## 4. Replace the validation handler, carefully

Invalid path, query or body data raises `RequestValidationError`, and `exc.errors()` gives the list you know from the 422 body. The obvious handler has a bug:

```python
@app.exception_handler(RequestValidationError)
async def naive_validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"errors": exc.errors()})
```

With `Poll.question` validated by a `field_validator` that raises `ValueError`:

```console
$ # POST /polls {"question": "lunch"}
TypeError Object of type ValueError is not JSON serializable
$ # POST /polls {}
422 {"errors":[{"type":"missing","loc":["body","question"],"msg":"Field required","input":{}}]}
```

Two problems:

1. **It crashes on custom validators.** For a `value_error`, the error's `ctx` holds the original `ValueError` *object*, which `JSONResponse` can't serialise. Your 422 becomes a 500 exactly when your own rules fire. (The docs' example passes the errors through `jsonable_encoder` to avoid this.)
2. **It echoes `input`.** The docs warn that dumping the error can leak information. On a sign-up form, `input` is the whole body, including the password.

The fix is to **pick the fields you want** instead of passing the list through:

```python
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    problems = [{"where": ".".join(map(str, e["loc"])), "problem": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"code": "invalid_request", "message": "see errors", "errors": problems},
    )
```

```console
POST /polls -> 422 {'code': 'invalid_request', 'message': 'see errors', 'errors': [{'where': 'body.question', 'problem': 'Value error, question must end with ?'}]}
```

Only strings go into the response, so it can't crash on serialisation, and no input is echoed.

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "After adding a custom RequestValidationError handler, most invalid requests still get a 422, but requests that break a `@field_validator` rule now crash with `TypeError: Object of type ValueError is not JSON serializable`. Why?",
  "options": ["field_validator errors aren't RequestValidationErrors", "The handler puts exc.errors() into the response as is, and a value_error's ctx holds the ValueError object", "ValueError must be replaced by HTTPException inside validators", "The handler must be a def, not async def"], "answer": 1,
  "explanation": "Errors from your own validators carry the original exception in ctx. Copy only JSON-safe fields (loc, type, msg) or pass the list through jsonable_encoder." }
```

## 5. 422 or 400?

RFC 9110 separates them:

- **400 Bad Request**: the server can't or won't process the request due to a client error, "e.g., malformed request syntax".
- **422 Unprocessable Content**: the server understands the content type, "the syntax of the request content is correct", but it can't process the instructions.

By that reading, `{"question": "lunch?",}` (a trailing comma, so not JSON at all) is a 400, and `{"question": 5}` (valid JSON, wrong type) is a 422. FastAPI doesn't split them. With a default app:

```console
$ # body: {"question": "lunch?",}   (content-type: application/json)
422 {'detail': [{'type': 'json_invalid', 'loc': ['body', 22], 'msg': 'JSON decode error', 'input': {}, 'ctx': {'error': 'Expecting property name enclosed in double quotes'}}]}
$ # body: {"question": 5}
422 {'detail': [{'type': 'string_type', 'loc': ['body', 'question'], 'msg': 'Input should be a valid string', 'input': 5}]}
```

Both are 422, and the malformed one is recognisable only by its error `type`, `json_invalid` (its `loc` is a character position, 22).

The two defensible policies:

| Policy | For | Against |
|---|---|---|
| Keep FastAPI's 422 for everything | zero code; matches FastAPI docs and generated OpenAPI | malformed syntax gets a code the RFC describes for *correct* syntax |
| 400 for `json_invalid`, 422 for the rest | follows RFC 9110 literally; clients can tell "broken client" from "user typed a bad value" | a few lines in the validation handler; must be documented |

Many APIs also use 400 for *all* validation errors, which is legal (400 is the generic client error) but less precise. What matters most is that it's **consistent and documented**. This course uses the second policy, and the exercise implements it. Whatever you choose, note that `/openapi.json` still describes FastAPI's default 422 schema unless you document your format yourself; the installed version lists a `422` response for a body endpoint regardless of your handler.

```quiz
{ "id": "q5", "type": "choice", "label": "Application",
  "prompt": "Under the course's policy (400 for malformed JSON, 422 for invalid values), which response fits `POST /chats` with the body `{\"title\": \"Team\"` (closing brace missing)?",
  "options": ["400, with a code like malformed_json", "422, with loc ['body', 'title']", "415 Unsupported Media Type", "500, because the JSON parser failed"], "answer": 0,
  "explanation": "The body isn't syntactically valid JSON, so this is malformed syntax (RFC 9110 400). FastAPI reports it as a RequestValidationError of type json_invalid, which the handler maps to 400." }
```

```quiz
{ "id": "q6", "type": "truefalse",
  "prompt": "With a default FastAPI app, a request body that is not valid JSON gets status 400.",
  "answer": false,
  "explanation": "FastAPI answers 422 with an error of type json_invalid. Getting 400 takes a custom RequestValidationError handler." }
```

## 6. Your turn: install one error format

The exercise gives you a small chats API that raises a domain exception, `HTTPException`, and triggers validation errors. You write `install_error_handlers(app)`, which makes every one of those responses use the nested format from the exercise, keeps headers, applies the 400/422 policy, and never echoes input.

```exercise
WEB.M02.L04.E1
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "A teammate proposes returning 200 for every request and putting `{\"ok\": false, \"error\": ...}` in the body, \"so clients only check one thing\". What do you answer?",
  "model": "Status codes are what HTTP clients, proxies, caches, retries, logs and monitoring understand without parsing the body. With 200 for everything, a cache might store an error, a retry policy can't tell a 503 from success, and dashboards show 0% errors. Keep real status codes and add one consistent body format for the details, which already gives clients one thing to parse.",
  "explanation": "A consistent body format complements status codes; it doesn't replace them." }
```
