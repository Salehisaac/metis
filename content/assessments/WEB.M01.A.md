---
{ "id": "WEB.M01.A", "module": "WEB.M01", "title": "WEB.M01 module assessment: FastAPI routing, methods, status codes and error bodies", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before WEB.M02.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "The routes are declared in this order. What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\n@app.get(\"/chats/{chat_id}\")\ndef read_chat(chat_id: int):\n    return {\"id\": chat_id}\n\n@app.get(\"/chats/archived\")\ndef archived():\n    return []\n\nr = TestClient(app).get(\"/chats/archived\")\nprint(r.status_code, r.json()[\"detail\"][0][\"loc\"])",
  "answer": "422 ['path', 'chat_id']",
  "explanation": "Routes are tried in declaration order. /chats/{chat_id} matches first, then \"archived\" fails the int conversion. FastAPI doesn't fall through to the next route. Declare /chats/archived first." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "from fastapi import FastAPI\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\n@app.get(\"/chats/{chat_id}/members\")\ndef members(chat_id: int, limit: int = 5, admins: bool | None = None):\n    return {\"chat_id\": chat_id, \"limit\": limit, \"admins\": admins}\n\nc = TestClient(app)\nprint(c.get(\"/chats/3/members?admins=off\").json())\nprint(c.get(\"/chats/3/members?limit=two\").status_code)",
  "answer": "{'chat_id': 3, 'limit': 5, 'admins': False}\n422",
  "explanation": "limit keeps its default 5, \"off\" is a false value for bool, and the path id is converted to int. \"two\" isn't an int, so the second request is 422." }
```

```quiz
{ "id": "a3", "type": "choice",
  "prompt": "`POST /chats` creates chat 12. Which response follows RFC 9110 best?",
  "options": ["200 with the chat in the body", "201 with `Location: /chats/12` and the chat in the body", "204 with `Location: /chats/12`", "202 with the chat in the body"], "answer": 1,
  "explanation": "A POST that creates a resource SHOULD answer 201 with a Location header identifying it (RFC 9110 9.3.3). The body typically describes the new resource." }
```

```quiz
{ "id": "a4", "type": "truefalse",
  "prompt": "In a path operation, `return HTTPException(status_code=404, detail=\"chat not found\")` sends a 404 response to the client.",
  "answer": false,
  "explanation": "Returning it makes it ordinary data: the client gets 200 with a body like {\"status_code\": 404, ...}. HTTPException must be raised." }
```

```quiz
{ "id": "a5", "type": "choice", "label": "Debugging",
  "prompt": "`def set_title(chat_id: int, title: str)` under `@app.put(\"/chats/{chat_id}/title\")`. The client sends `{\"title\": \"Team\"}` as JSON and gets 422 with `loc` `['query', 'title']`, type `missing`. What's the fix?",
  "options": ["Send title in the query string from now on, because the route is correct", "Declare a Pydantic model with a title field and use it as the body parameter", "Change the method to POST", "Add status_code=200 to the decorator"], "answer": 1,
  "explanation": "A parameter typed as a single str is a query parameter, so FastAPI never looks in the JSON body. To read it from the body, it must be a field of a BaseModel parameter." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Design the responses of `POST /chats/{chat_id}/members` with body `{\"user_id\": int}`: success, chat doesn't exist, user is already a member, body without user_id. Give a status code and a one-line reason for each.",
  "model": "Success: 201 Created (a membership was created), with Location such as /chats/{chat_id}/members/{user_id}. Unknown chat: 404, since the target resource doesn't exist. Already a member: 409 Conflict, because the request conflicts with the current state (some APIs choose 200 to make it idempotent; either way, document it). Missing user_id: 422 from FastAPI's validation, with loc ['body', 'user_id'].",
  "explanation": "Each failure gets a distinct code and a body that says what to fix." }
```
