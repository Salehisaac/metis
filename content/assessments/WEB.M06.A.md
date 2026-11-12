---
{ "id": "WEB.M06.A", "module": "WEB.M06", "title": "WEB.M06 module assessment: authentication and authorization", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before moving on.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "from datetime import datetime, timedelta, timezone\nimport jwt\n\nkey = \"k\" * 32\nnow = datetime.now(timezone.utc)\ngood = jwt.encode({\"sub\": \"7\", \"aud\": \"chat-api\", \"exp\": now + timedelta(minutes=5)}, key, algorithm=\"HS256\")\nold = jwt.encode({\"sub\": \"7\", \"aud\": \"chat-api\", \"exp\": now - timedelta(minutes=5)}, key, algorithm=\"HS256\")\nfor token, k in ((good, key), (good, \"x\" * 32), (old, key)):\n    try:\n        print(jwt.decode(token, k, algorithms=[\"HS256\"], audience=\"chat-api\")[\"sub\"])\n    except jwt.InvalidTokenError as exc:\n        print(type(exc).__name__)",
  "answer": "7\nInvalidSignatureError\nExpiredSignatureError",
  "explanation": "The right key and audience give the claims. Another key fails the signature check. An exp in the past raises ExpiredSignatureError. All are InvalidTokenError subclasses, which a FastAPI dependency turns into 401." }
```

```quiz
{ "id": "a2", "type": "choice",
  "prompt": "Which way of storing passwords is acceptable?",
  "options": ["scrypt with a random per-user salt, with the parameters and salt stored next to the derived key", "sha256(password + a fixed app-wide salt)", "AES-encrypted passwords with the key in an environment variable", "bcrypt-hashed passwords compared with == against the stored string after rehashing with a new salt"], "answer": 0,
  "explanation": "A slow, salted, tunable key-derivation function with the salt and parameters stored is the OWASP pattern. A fast hash with one salt allows billions of guesses and shared hashes; encryption is reversible; and rehashing with a new salt can never match." }
```

```quiz
{ "id": "a3", "type": "truefalse",
  "prompt": "`jwt.decode(token, options={\"verify_signature\": False})` is fine for reading the user's role, as long as the token came over HTTPS.", "answer": false,
  "explanation": "HTTPS protects the token in transit, not its origin. Anyone can create a token with any payload. Only signature verification with the server's key and algorithm list makes the claims trustworthy." }
```

```quiz
{ "id": "a4", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI, Header, HTTPException\nfrom fastapi.testclient import TestClient\n\nUSERS = {\"a\": \"admin\", \"u\": \"user\"}\n\ndef current_role(authorization: Annotated[str | None, Header()] = None) -> str:\n    role = USERS.get((authorization or \"\").removeprefix(\"Bearer \"))\n    if role is None:\n        raise HTTPException(status_code=401)\n    return role\n\ndef require(*roles: str):\n    def check(role: Annotated[str, Depends(current_role)]) -> str:\n        if role not in roles:\n            raise HTTPException(status_code=403)\n        return role\n    return check\n\napp = FastAPI()\n\n@app.post(\"/admin/users/9/ban\")\ndef ban(role: Annotated[str, Depends(require(\"admin\"))]):\n    return {\"by\": role}\n\nclient = TestClient(app)\nfor h in ({}, {\"Authorization\": \"Bearer u\"}, {\"Authorization\": \"Bearer a\"}):\n    print(client.post(\"/admin/users/9/ban\", headers=h).status_code)",
  "answer": "401\n403\n200",
  "explanation": "No identity: 401, raised by current_role before the role check runs. A known user without the role: 403. The admin: 200." }
```

```quiz
{ "id": "a5", "type": "choice", "label": "Debugging",
  "prompt": "`GET /chats/{chat_id}/messages` requires a valid token and returns the chat's messages. Eve, who isn't a member of chat 3, gets chat 3's messages by changing the URL. What's missing?",
  "options": ["An object-level check that Eve is a member of chat 3 (answering 404 to outsiders)", "A role check for admins", "Token expiry", "A 401 for Eve"], "answer": 0,
  "explanation": "This is an IDOR. Eve is authenticated, so 401 is wrong. The endpoint must check access to this specific chat on every request." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "A pull request adds `SECRET_KEY = \"9f2c...\"` to settings.py, and `def get_current_user(token)` that returns `jwt.decode(token, SECRET_KEY, algorithms=[\"HS256\"])[\"sub\"]` without any try/except. List what you'd ask the author to change, and why.",
  "model": "1) Remove the secret from the code: load it at runtime from injected configuration (an env var or a secrets manager) and fail closed if it's missing or short; since it was committed, rotate it. 2) Catch jwt.InvalidTokenError and turn it into 401 with WWW-Authenticate: Bearer, or every bad or expired token becomes a 500. 3) Verify audience and issuer and require exp/sub. 4) Look the user up and return 401 if they no longer exist (or are banned), instead of trusting sub alone. 5) Add tests: missing token, garbage, expired, other key and deleted user give 401.",
  "explanation": "A good review covers the secret, error mapping, claim validation, the user lookup and the missing tests." }
```
