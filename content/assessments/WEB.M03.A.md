---
{ "id": "WEB.M03.A", "module": "WEB.M03", "title": "WEB.M03 module assessment: dependency injection and app structure", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before WEB.M04.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.testclient import TestClient\n\ncalls = []\n\ndef settings():\n    calls.append(\"settings\")\n    return {\"max_len\": 10}\n\ndef validator(s: Annotated[dict, Depends(settings)]):\n    return s[\"max_len\"]\n\napp = FastAPI()\n\n@app.post(\"/messages\")\ndef send(text: str, s: Annotated[dict, Depends(settings)], max_len: Annotated[int, Depends(validator)]):\n    return {\"ok\": len(text) <= max_len}\n\nc = TestClient(app)\nprint(c.post(\"/messages?text=hello\").json())\nprint(len(calls))",
  "answer": "{'ok': True}\n1",
  "explanation": "settings is needed twice in one request (directly and through validator), but FastAPI calls it once per request and reuses the value." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI, HTTPException\nfrom fastapi.testclient import TestClient\n\nlog = []\n\ndef get_session():\n    log.append(\"open\")\n    try:\n        yield \"session\"\n    except Exception:\n        log.append(\"rollback\")\n        raise\n    finally:\n        log.append(\"close\")\n\napp = FastAPI()\n\n@app.post(\"/chats/{chat_id}/leave\")\ndef leave(chat_id: int, session: Annotated[str, Depends(get_session)]):\n    if chat_id == 1:\n        raise HTTPException(status_code=409, detail=\"owner cannot leave\")\n    return {\"left\": chat_id}\n\nr = TestClient(app).post(\"/chats/1/leave\")\nprint(r.status_code, log)",
  "answer": "409 ['open', 'rollback', 'close']",
  "explanation": "The HTTPException is raised at the yield: except rolls back and re-raises, finally closes, and FastAPI turns the re-raised exception into the 409." }
```

```quiz
{ "id": "a3", "type": "choice",
  "prompt": "Why should the endpoint commit before returning, instead of the yield dependency committing after its yield?",
  "options": ["Commits after yield are not allowed by Python", "Code after the yield runs after the response is created, so a failed commit there can't change the success status the client gets", "FastAPI skips code after yield on success", "Committing in the endpoint is faster"], "answer": 1,
  "explanation": "The docs: code after yield runs after the response. A commit that fails there still leaves the client with 201 for unsaved data." }
```

```quiz
{ "id": "a4", "type": "truefalse",
  "prompt": "`app.dependency_overrides[get_current_user] = lambda: test_user` also replaces get_current_user inside sub-dependencies such as a membership check that declares it.",
  "answer": true,
  "explanation": "An override replaces the dependency wherever it appears in the dependency tree." }
```

```quiz
{ "id": "a5", "type": "choice",
  "prompt": "An endpoint needs an authenticated user (else 401), then the chat (else 404), then membership (else 403). Which design fits this module best?",
  "options": ["Read the header and check everything inside each endpoint", "A get_member_chat dependency that declares the current-user dependency as a parameter and raises 404/403; endpoints declare get_member_chat", "A global variable holding the current user", "Check membership in the repository's get method"], "answer": 1,
  "explanation": "Sub-dependencies give the order (authentication first), keep the checks in one place, and can be overridden in tests." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Sketch the files and responsibilities for a 'pinned messages' feature (pin, unpin, list) in the structure from L03, and say which dependency a test would override to start each test with empty storage.",
  "model": "pins_router.py: APIRouter(prefix=\"/chats/{chat_id}/pins\", tags=[\"pins\"]), request/response models, one service call per endpoint. services.py: PinService(repo) with pin/unpin/list and rules (max pins per chat, message must belong to the chat), raising domain exceptions; no FastAPI. repository.py: PinRepository storage. deps.py: cached get_pin_repository and get_pin_service(repo=Depends(get_pin_repository)), plus the current user and membership dependencies. main.py: include the router and map domain exceptions to status codes. Tests override get_pin_repository with a lambda returning one fresh repository per test.",
  "explanation": "Rules in services, HTTP in routers, wiring in dependencies, storage swappable through one override." }
```
