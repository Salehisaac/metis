---
{
  "id": "WEB.M01.L02",
  "title": "Methods and status codes in FastAPI",
  "difficulty": "beginner",
  "minutes": 110,
  "prerequisites": ["WEB.M01.L01"],
  "objectives": [
    "Choose the method and success code for create, read, replace and delete, and justify them with RFC 9110",
    "Return 201 with a Location header, and 204 with an empty body, from FastAPI",
    "Raise HTTPException for 404 and 409 and predict the response body",
    "Tell which parameters FastAPI reads from the path, the query and the JSON body",
    "Predict FastAPI's automatic 405 and its Allow header"
  ],
  "why": "Clients, proxies and retry logic act on the method and the status code, not on your JSON. A create that answers 200, a missing resource that answers 200 with null, or a delete that can't be retried safely all turn into bugs in someone else's code. You know these rules from Go; this lesson is about getting FastAPI to send exactly the code you mean.",
  "applications": [
    "CRUD endpoints for chats, users and messages",
    "Duplicate usernames or chat titles (409)",
    "Safe client retries after a timeout"
  ],
  "exercises": ["WEB.M01.L02.E1"],
  "sources": [
    {
      "title": "RFC 9110: HTTP Semantics (sections 9.2, 9.3, 15)",
      "url": "https://www.rfc-editor.org/rfc/rfc9110.html",
      "version": "RFC 9110 (June 2022, STD 97)",
      "verified": "2026-11-12",
      "claims": ["9.2.1: GET, HEAD, OPTIONS and TRACE are safe", "9.2.2: PUT, DELETE and the safe methods are idempotent; idempotent requests can be repeated automatically after a communication failure", "9.3.3: when POST creates a resource, the server SHOULD send 201 with a Location header", "9.3.4: PUT that creates sends 201; PUT that modifies sends 200 or 204", "15.3.2: 201 means one or more resources were created, identified by Location or the target URI", "15.3.5: a 204 response cannot contain content", "15.5.5: 404 means no current representation was found for the target", "15.5.6: the server MUST generate an Allow header in a 405 response", "15.5.10: 409 means the request conflicts with the current state of the target resource"]
    },
    {
      "title": "FastAPI Tutorial: Request Body",
      "url": "https://fastapi.tiangolo.com/tutorial/body/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["A request body is declared as a parameter whose type is a Pydantic BaseModel", "Parameters in the path are path parameters, singular types are query parameters, Pydantic models are the body", "Sending a body with GET is discouraged"]
    },
    {
      "title": "FastAPI Tutorial: Response Status Code",
      "url": "https://fastapi.tiangolo.com/tutorial/response-status-code/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["status_code is a parameter of the decorator, not of the function", "fastapi.status holds named constants such as HTTP_201_CREATED", "204 means the response must not have a body"]
    },
    {
      "title": "FastAPI Tutorial: Handling Errors",
      "url": "https://fastapi.tiangolo.com/tutorial/handling-errors/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["HTTPException is raised, not returned; raising stops the path operation", "The client receives the status code and a JSON body {\"detail\": ...}"]
    },
    {
      "title": "FastAPI Advanced: Response Headers",
      "url": "https://fastapi.tiangolo.com/advanced/response-headers/",
      "version": "FastAPI docs (page states no version; installed 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Declare a Response parameter, set headers on it, and return data as usual; FastAPI copies the headers into the final response"]
    }
  ]
}
---
## 1. Method semantics, in one table

You got PUT idempotency and 409 right in the assessment, so this is a recap. RFC 9110 defines two properties:

| Method | Safe (read-only) | Idempotent (repeat = same effect on the server) | Typical success code |
|---|---|---|---|
| GET | yes | yes | 200 |
| POST | no | no | 201 + `Location` when it creates |
| PUT | no | yes | 200 or 204 (201 if it created the resource) |
| PATCH | no | not in RFC 9110's idempotent list | 200 |
| DELETE | no | yes | 204 (or 200 with a body) |

The practical consequence, in the RFC's words: an idempotent request "can be repeated automatically if a communication failure occurs". A client that timed out on `DELETE /messages/7` may resend it. A client that timed out on `POST /messages` may not, or the message is sent twice.

Idempotent is about the **server state**, not the response. A second DELETE of the same message changes nothing more, but it may well answer 404 instead of 204. You'll see exactly that in section 4.

FastAPI's own docs say it "doesn't enforce any specific meaning" for methods. `@app.get` on a function that deletes data works. Getting it right is your job.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A mobile client times out waiting for a response. Which request can it resend automatically without risking a duplicate effect?",
  "options": ["POST /chats/4/messages", "DELETE /chats/4/messages/31", "POST /chats/4/members", "PATCH /users/me with {\"unread_count\": \"+1\"}"], "answer": 1,
  "explanation": "DELETE is idempotent (RFC 9110 9.2.2): deleting message 31 twice leaves the same state as once. The POSTs create a new thing each time, and an increment PATCH adds again." }
```

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "Because DELETE is idempotent, the second identical DELETE must return the same status code as the first.",
  "answer": false,
  "explanation": "Idempotency is about the effect on server state. The first DELETE removes the resource (204); the second finds nothing and can return 404, while the state is unchanged." }
```

## 2. Where FastAPI reads each parameter from

To create something, the client sends a JSON body. In FastAPI you describe the body as a class that inherits from Pydantic's `BaseModel` (the whole of WEB.M02 is about these models; here you only need the basic form):

```python
from pydantic import BaseModel


class NewUser(BaseModel):
    username: str
    display_name: str
```

FastAPI then decides the source of each function parameter by these rules:

1. Its name appears in the path (`{user_id}`) → **path** parameter.
2. Its type is a single value (`int`, `str`, `bool`, `float`) → **query** parameter.
3. Its type is a Pydantic model → **JSON body**.

In Go you'd `json.NewDecoder(r.Body).Decode(&req)` and check the error yourself. Here a body that's missing a field or has the wrong type is rejected with 422 before your function runs.

**Common mistake:** writing `def rename(chat_id: int, title: str)` and sending `{"title": "x"}` as JSON. `title` is a single `str`, so FastAPI looks for it in the **query string**, doesn't find it, and answers 422 `missing` with `loc` `["query", "title"]`. If it should come from the body, it has to be a field of a model.

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "`@app.post(\"/chats/{chat_id}/messages\")` on `def send(chat_id: int, body: NewMessage, silent: bool = False)`, where NewMessage is a BaseModel. Where does FastAPI read `silent` from?",
  "options": ["The path", "The query string, e.g. ?silent=true", "The JSON body, as a field next to the message fields", "A header"], "answer": 1,
  "explanation": "silent isn't in the path and its type is a single bool, so it's a query parameter. Only parameters typed as Pydantic models come from the body." }
```

## 3. 201 Created with a Location header

Here is a small user API you can run. It uses the `NewUser` model from section 2:

```python
# users_api.py
import itertools

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI()


class NewUser(BaseModel):
    username: str
    display_name: str


users: dict[int, dict] = {}
_ids = itertools.count(1)


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(body: NewUser, response: Response):
    if any(u["username"] == body.username for u in users.values()):
        raise HTTPException(status_code=409, detail="username already taken")
    user = {"id": next(_ids), "username": body.username, "display_name": body.display_name}
    users[user["id"]] = user
    response.headers["Location"] = f"/users/{user['id']}"
    return user


@app.get("/users/{user_id}")
def read_user(user_id: int):
    if user_id not in users:
        raise HTTPException(status_code=404, detail="user not found")
    return users[user_id]


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int):
    if users.pop(user_id, None) is None:
        raise HTTPException(status_code=404, detail="user not found")
```

Two things set the success response:

- **`status_code=` in the decorator** is the code for the normal return path. Without it, every success is 200. `status.HTTP_201_CREATED` is just the number 201 with a name your editor can autocomplete.
- **A `Response` parameter** gives you a temporary response object. Headers you set on it are copied into the real response, and you still return plain data. RFC 9110 says a POST that creates a resource SHOULD answer 201 with a `Location` header naming it, so the client knows the new URL without guessing.

`itertools.count(1)` is an endless counter: each `next(_ids)` gives 1, 2, 3, and so on. It's the in-memory stand-in for an auto-increment column.

Driving it with `TestClient` and printing method, path, status, Location and the raw body:

```console
POST /users -> 201 /users/1 b'{"id":1,"username":"ali","display_name":"Ali"}'
POST /users -> 409 None b'{"detail":"username already taken"}'
```

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI, Response\nfrom fastapi.testclient import TestClient\nfrom pydantic import BaseModel\n\nclass Reaction(BaseModel):\n    emoji: str\n\napp = FastAPI()\n\n@app.post(\"/messages/{message_id}/reactions\", status_code=201)\ndef react(message_id: int, body: Reaction, response: Response):\n    response.headers[\"Location\"] = f\"/messages/{message_id}/reactions/{body.emoji}\"\n    return {\"message_id\": message_id, \"emoji\": body.emoji}\n\nr = TestClient(app).post(\"/messages/8/reactions\", json={\"emoji\": \"fire\"})\nprint(r.status_code, r.headers[\"location\"])\nprint(r.json())",
  "answer": "201 /messages/8/reactions/fire\n{'message_id': 8, 'emoji': 'fire'}",
  "explanation": "The decorator's status_code sets 201; the header set on the Response parameter is copied into the real response; the returned dict becomes the JSON body. Header names are case-insensitive, so \"location\" finds \"Location\"." }
```

## 4. Errors: raise HTTPException, don't return it

For "not found" and "conflict" you **raise** `HTTPException(status_code=..., detail=...)`. It works like returning an error early in a Go handler: the rest of the function doesn't run, and the client gets that status with the body `{"detail": ...}`.

```console
GET /users/1 -> 200 None b'{"id":1,"username":"ali","display_name":"Ali"}'
GET /users/2 -> 404 None b'{"detail":"user not found"}'
DELETE /users/1 -> 204 None b''
DELETE /users/1 -> 404 None b'{"detail":"user not found"}'
```

Look at the two DELETEs: same request, 204 then 404, same final state. That's the idempotency from section 1.

**Common mistake: `return HTTPException(...)`.** Go habits make this easy to type, because in Go you return errors. In FastAPI the exception object is then treated as ordinary data:

```python
@app.get("/stickers/{sticker_id}")
def read_sticker(sticker_id: int):
    if sticker_id != 1:
        return HTTPException(status_code=404, detail="sticker not found")
    return {"id": 1, "emoji": "cat"}
```

```console
200 {'status_code': 404, 'detail': 'sticker not found', 'headers': None}
```

The client gets **200** with an object that merely *contains* 404. A client checking the status code sees success.

Which code for which failure? 404 when the target doesn't exist. 409 when the request is well-formed but conflicts with the current state: a username that's taken, deleting a user who still owns chats, editing a message that was already deleted by someone else. (400 vs 422 for malformed input is a WEB.M02 topic.)

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI, HTTPException\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\ncontacts = {1: \"sara\", 2: \"omid\"}\n\n@app.delete(\"/contacts/{contact_id}\", status_code=204)\ndef remove_contact(contact_id: int):\n    if contacts.pop(contact_id, None) is None:\n        raise HTTPException(status_code=404, detail=\"contact not found\")\n\nc = TestClient(app)\nfor _ in range(2):\n    r = c.delete(\"/contacts/2\")\n    print(r.status_code, r.content)",
  "answer": "204 b''\n404 b'{\"detail\":\"contact not found\"}'",
  "explanation": "The first call pops contact 2 and falls off the end: the decorator's 204, with an empty body. The second pop returns None, so the HTTPException gives 404 and a {\"detail\": ...} body. r.content is raw bytes, and FastAPI writes compact JSON with no spaces." }
```

```quiz
{ "id": "q6", "type": "choice", "label": "Application",
  "prompt": "Your rule: a user who still owns group chats can't be deleted. A client sends `DELETE /users/5` for such a user. Which response fits best?",
  "options": ["200 with {\"deleted\": false}", "404 Not Found", "409 Conflict with a detail that says the user still owns chats", "500 Internal Server Error"], "answer": 2,
  "explanation": "The user exists and the request is well-formed, but it conflicts with the current state (RFC 9110 15.5.10). The detail tells the client what to resolve. 200 hides the failure; 404 is false; 500 blames the server." }
```

## 5. 204 and 405: what FastAPI does for you

**204 No Content.** RFC 9110 says a 204 response "cannot contain content". `delete_user` returns nothing (`None`), and with `status_code=204` FastAPI sends an empty body, as the `b''` above shows. Don't return a dict from a 204 route; if you need to send data back, use 200.

**405 Method Not Allowed.** If the path exists but no route has that method, FastAPI answers 405 without your code running:

```console
$ # PATCH /users/1 on the app above
405 GET {'detail': 'Method Not Allowed'}
```

The middle value is the `Allow` header, which RFC 9110 says a 405 response MUST include. Notice it says only `GET`, even though `DELETE /users/{user_id}` exists too. With the installed versions, each decorator is a separate route, and the header lists the methods of the **first** route whose path matched. (Declaring both methods on one route, with `@app.api_route(path, methods=["GET", "DELETE"])`, lists both.) It's a small gap between the framework and the RFC. Know it's there; don't build a client that relies on `Allow`.

```quiz
{ "id": "q7", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\n@app.get(\"/chats/{chat_id}\")\ndef read_chat(chat_id: int):\n    return {\"id\": chat_id}\n\nr = TestClient(app).delete(\"/chats/3\")\nprint(r.status_code, r.headers[\"allow\"])",
  "answer": "405 GET",
  "explanation": "The path matches but no route accepts DELETE, so FastAPI answers 405 and lists the allowed method in the Allow header." }
```

## 6. Your turn: a chats resource with correct codes

The exercise is a complete small resource: create, read, rename and delete chats, with a 409 for duplicate titles. Read the edge cases carefully: renaming a chat to its *own* current title is the one people get wrong.

```exercise
WEB.M01.L02.E1
```

```quiz
{ "id": "q8", "type": "explain", "label": "Application",
  "prompt": "Why should `POST /users` answer 201 with a Location header instead of 200, if the body already contains the new id?",
  "model": "201 states the outcome: something new was created, which generic clients, proxies, logs and API docs understand without reading the body. Location gives the canonical URL, so clients don't have to know how to build /users/{id} from the body. RFC 9110 says a creating POST SHOULD do this.",
  "explanation": "Status codes and headers are the part of the contract every HTTP client understands." }
```
