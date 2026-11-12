---
{
  "id": "WEB.M06.L03",
  "title": "Login and the current user: OAuth2PasswordBearer",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["WEB.M06.L02", "WEB.M03"],
  "objectives": [
    "Describe the bearer-token flow: a login endpoint issues a token, and every later request sends it in the Authorization header",
    "Accept OAuth2 password-flow credentials as form fields with OAuth2PasswordRequestForm, and send them from a test with data=",
    "Use OAuth2PasswordBearer to read the bearer token, and predict its 401 response when the header is missing or isn't Bearer",
    "Write a get_current_user dependency that maps every invalid-token case to the same 401 with WWW-Authenticate: Bearer",
    "Write a login endpoint that reveals neither which usernames exist nor which credential was wrong, through its message or its timing",
    "Test authenticated endpoints with real tokens for the auth paths, and with dependency_overrides for everything else"
  ],
  "why": "Lessons 1 and 2 built the parts: password hashes and signed tokens. This lesson wires them into FastAPI the way the official tutorial does. Afterwards, any endpoint becomes 'logged-in users only' by adding one parameter. Getting the edges right (every bad token gets the same 401, login doesn't leak usernames) is what separates a demo from an API you can expose to the internet.",
  "applications": [
    "Login and 'who am I' endpoints for the chat API's mobile and web clients",
    "Protecting every chat and message route with a current-user dependency",
    "Bot or service tokens checked by the same mechanism with a different audience"
  ],
  "exercises": ["WEB.M06.L03.E1"],
  "sources": [
    {
      "title": "FastAPI Tutorial: Security - First Steps",
      "url": "https://fastapi.tiangolo.com/tutorial/security/first-steps/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": [
        "OAuth2PasswordBearer(tokenUrl=...) declares the URL clients use to get a token; it doesn't create that endpoint; tokenUrl is relative",
        "The dependency looks for an Authorization header with the value Bearer plus a token, and returns the token as a str",
        "Without an Authorization header, or without a Bearer token, it responds with 401 directly"
      ]
    },
    {
      "title": "FastAPI Tutorial: Simple OAuth2 with Password and Bearer",
      "url": "https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": [
        "The OAuth2 password flow sends username and password as form data, not JSON; OAuth2PasswordRequestForm is a class dependency that declares username, password and an optional scope",
        "The token response is JSON with access_token and token_type \"bearer\"",
        "Unknown user and wrong password return the same error, \"Incorrect username or password\" (status 400 in the code)",
        "A 401 is supposed to return a WWW-Authenticate header, with the value Bearer for bearer tokens",
        "get_current_active_user returns 400 \"Inactive user\" for a disabled user"
      ]
    },
    {
      "title": "FastAPI Tutorial: OAuth2 with Password (and hashing), Bearer with JWT tokens",
      "url": "https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": [
        "get_current_user decodes the JWT, and turns InvalidTokenError or a missing sub into a 401 credentials exception with WWW-Authenticate: Bearer",
        "For an unknown username, authenticate_user still verifies against a dummy hash so the response takes about as long, preventing timing attacks that enumerate usernames"
      ]
    },
    {
      "title": "FastAPI Advanced: Testing Dependencies with Overrides",
      "url": "https://fastapi.tiangolo.com/advanced/testing-dependencies/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["An external authentication dependency can be overridden with one that returns a fixed user, only for tests"]
    },
    {
      "title": "OWASP REST Security Cheat Sheet",
      "url": "https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html",
      "version": "OWASP Cheat Sheet Series (current)",
      "verified": "2026-11-12",
      "claims": [
        "401 Unauthorized: wrong or no authentication provided",
        "Passwords, security tokens and API keys should not appear in the URL"
      ]
    }
  ]
}
---
## 1. The bearer-token flow

1. The client sends a username and password **once**, to a login endpoint.
2. The server checks them (lesson 1) and returns a signed, short-lived token (lesson 2): `{"access_token": "...", "token_type": "bearer"}`.
3. On every later request, the client sends `Authorization: Bearer <token>`. The server verifies the token and knows who's calling, without a session table and without the password.

Tokens go in a header, never in the URL: URLs end up in server logs and browser history (OWASP REST Security Cheat Sheet).

FastAPI's `OAuth2PasswordBearer` does the header part:

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


@app.get("/whoami")
def whoami(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}
```

- It reads `Authorization`, checks for `Bearer <something>` and gives you the token as a string. **It doesn't verify anything:** the string could be garbage. Verifying is your dependency's job (section 3).
- No header, or a different scheme (`Basic ...`), gets a 401 straight away, before your code runs.
- `tokenUrl` only tells the interactive docs (`/docs`) where to log in. It doesn't create the endpoint.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.security import OAuth2PasswordBearer\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\noauth2_scheme = OAuth2PasswordBearer(tokenUrl=\"auth/token\")\n\n@app.get(\"/whoami\")\ndef whoami(token: Annotated[str, Depends(oauth2_scheme)]):\n    return {\"token\": token}\n\nclient = TestClient(app)\nr = client.get(\"/whoami\")\nprint(r.status_code, r.json()[\"detail\"], r.headers[\"WWW-Authenticate\"])\nprint(client.get(\"/whoami\", headers={\"Authorization\": \"Basic YWxpOnB3\"}).status_code)\nprint(client.get(\"/whoami\", headers={\"Authorization\": \"Bearer abc.def\"}).json())",
  "answer": "401 Not authenticated Bearer\n401\n{'token': 'abc.def'}",
  "explanation": "No header: 401 with WWW-Authenticate: Bearer. Basic isn't Bearer: 401. With Bearer, the scheme returns the raw string, here an obviously invalid token, because OAuth2PasswordBearer doesn't verify anything." }
```

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "`OAuth2PasswordBearer(tokenUrl=\"auth/token\")` creates the POST /auth/token endpoint for you.", "answer": false,
  "explanation": "It only declares where clients get a token, for the OpenAPI docs. You write the login endpoint yourself." }
```

## 2. The login endpoint

The FastAPI tutorial follows the OAuth2 "password flow", which requires the credentials as **form fields**, not JSON. `OAuth2PasswordRequestForm` is a class dependency that declares those fields (`username`, `password`, plus an optional `scope`). Form parsing needs the `python-multipart` package, which is installed in this project's venv. In a test you send form fields with `data=`:

```python
@app.post("/auth/token")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    if (form.username, form.password) != ("ali", "s3cret-pass"):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": "<a signed JWT>", "token_type": "bearer"}


client = TestClient(app)
print(client.post("/auth/token", data={"username": "ali", "password": "s3cret-pass"}).json())
print(client.post("/auth/token", data={"username": "ali", "password": "nope"}).json())
r = client.post("/auth/token", json={"username": "ali", "password": "s3cret-pass"})
print(r.status_code, [e["loc"] for e in r.json()["detail"]])
```

```console
{'access_token': '<a signed JWT>', 'token_type': 'bearer'}
{'detail': 'Incorrect username or password'}
422 [['body', 'username'], ['body', 'password']]
```

(The plain-text comparison is only there to keep the example short. A real endpoint looks the user up and calls `verify_password`, as below.)

Because the endpoint speaks standard OAuth2, the "Authorize" button in `/docs` and OAuth2 client libraries work with it. A JSON body is rejected with 422, as the last line shows. **Alternative:** an API used only by your own frontend can take JSON instead (a Pydantic model with `username` and `password`). That works the same way after login, but it isn't the standard flow.

```quiz
{ "id": "q7", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.security import OAuth2PasswordRequestForm\nfrom fastapi.testclient import TestClient\n\napp = FastAPI()\n\n@app.post(\"/auth/token\")\ndef login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):\n    return {\"access_token\": form.username.upper(), \"token_type\": \"bearer\"}\n\nclient = TestClient(app)\nprint(client.post(\"/auth/token\", data={\"username\": \"sara\", \"password\": \"pw\"}).json()[\"access_token\"])\nprint(client.post(\"/auth/token\", data={\"username\": \"sara\"}).status_code)\nprint(client.post(\"/auth/token\", json={\"username\": \"sara\", \"password\": \"pw\"}).status_code)",
  "answer": "SARA\n422\n422",
  "explanation": "data= sends form fields, so the form dependency gets username and password. Without a password field, validation fails: 422. A JSON body has no form fields at all, so it's 422 too: the password flow is form-only." }
```

What the endpoint must get right:

- **One error for both failures.** "Unknown user" and "wrong password" return the same status and message (the tutorial: 400, "Incorrect username or password"). Different messages tell an attacker which usernames exist.
- **The same amount of work for both.** If unknown usernames return instantly and wrong passwords take 70 ms of hashing, the timing reveals the same thing. The tutorial verifies against a **dummy hash** when the user doesn't exist.
- **Return only the token.** Never the password hash, never the user row.

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "A login endpoint answers \"no such user\" for unknown usernames and \"wrong password\" otherwise, both with 400. What's the problem?",
  "options": ["Attackers can find out which usernames exist, then target only those with password guesses", "400 is the wrong status for a failed login", "The password is sent in plain text", "Nothing: the messages help users"], "answer": 0,
  "explanation": "Different messages make account enumeration trivial. Use one generic message, and equal hashing work (a dummy hash) so the timing doesn't reveal it either." }
```

## 3. `get_current_user`: every bad token, one 401

The current-user dependency turns a token into a user. Here is the same pattern for **bot tokens** (bots post messages into chats). They use a different audience, so a user token can't act as a bot:

```python
def read_bot_token(token: str) -> dict:
    return jwt.decode(token, BOT_KEY, algorithms=["HS256"], audience="bot-api", options={"require": ["exp", "sub"]})


def get_current_bot(token: Annotated[str, Depends(bot_scheme)]) -> Bot:
    unauthorized = HTTPException(status_code=401, detail="Could not validate credentials",
                                 headers={"WWW-Authenticate": "Bearer"})
    try:
        bot_id = int(read_bot_token(token)["sub"].removeprefix("bot:"))
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized
    bot = BOTS.get(bot_id)
    if bot is None:
        raise unauthorized
    return bot


@app.post("/chats/{chat_id}/bot-messages", status_code=201)
def post_as_bot(chat_id: int, bot: Annotated[Bot, Depends(get_current_bot)]):
    return {"chat_id": chat_id, "from": bot.name}
```

```console
valid        201 {'chat_id': 1, 'from': 'standup-bot'}
expired      401 {'detail': 'Could not validate credentials'}
unknown bot  401 {'detail': 'Could not validate credentials'}
bad sub      401 {'detail': 'Could not validate credentials'}
garbage      401 {'detail': 'Could not validate credentials'}
```

- **Catch `jwt.InvalidTokenError`, the base class**, not each subclass. A new failure mode in a future PyJWT version is then still a 401, not a 500.
- **A genuine token for a deleted account is still a 401.** The signature is fine, but it no longer identifies anyone.
- **Same body for every case.** The client only needs to know "log in again"; the details belong in your logs.
- **`WWW-Authenticate: Bearer`** on every 401, as the FastAPI docs say every 401 should have.
- **Stack dependencies.** The tutorial's `get_current_active_user` depends on `get_current_user` and adds one rule (disabled users get 400 "Inactive user"). Endpoints pick the layer they need. The next lesson adds role checks the same way.

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "A current-user dependency catches only `jwt.ExpiredSignatureError` and `jwt.InvalidSignatureError`. A client sends a correctly signed token for another audience. What does it get?",
  "options": ["500: InvalidAudienceError isn't caught, so it escapes as a server error", "401, because the signature is valid", "200, because the signature is valid", "403, because the audience is wrong"], "answer": 0,
  "explanation": "InvalidAudienceError isn't one of the two caught classes, so it propagates and becomes a 500. Catching the base class jwt.InvalidTokenError turns every token problem into a 401." }
```

## 4. Testing authenticated endpoints

Two kinds of tests, two techniques:

- **Tests about authentication** (login, 401 cases): use real tokens. Log in through the API, or create tokens with your token module, including deliberately broken ones (expired, other key, unknown user). A small `bearer(token)` helper that returns `{"Authorization": f"Bearer {token}"}` keeps them short. Put the test secret in the environment with `monkeypatch.setenv`, never in the app's code.
- **Tests about everything else** (sending messages, listing chats): override the current-user dependency, so they don't depend on login at all. The FastAPI docs suggest exactly this for authentication providers.

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI\nfrom fastapi.security import OAuth2PasswordBearer\nfrom fastapi.testclient import TestClient\n\noauth2_scheme = OAuth2PasswordBearer(tokenUrl=\"auth/token\")\n\ndef get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:\n    raise RuntimeError(\"would decode a real token\")\n\napp = FastAPI()\n\n@app.get(\"/chats\")\ndef my_chats(user: Annotated[str, Depends(get_current_user)]):\n    return {\"user\": user}\n\nclient = TestClient(app)\nprint(client.get(\"/chats\").status_code)\napp.dependency_overrides[get_current_user] = lambda: \"ali\"\nprint(client.get(\"/chats\").json())",
  "answer": "401\n{'user': 'ali'}",
  "explanation": "Without a header, oauth2_scheme (a sub-dependency of get_current_user) answers 401. The override replaces get_current_user together with its own dependencies, so no header is needed and the endpoint sees 'ali'." }
```

**Limitation:** an overridden current user skips the whole auth stack. So keep a few real-token tests for every protected router: at least "no token → 401" per route group. Otherwise a route that forgot the dependency entirely would never show up in tests.

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Your API has 30 protected endpoints. A teammate proposes overriding get_current_user in a global autouse fixture so no test ever deals with tokens. What do you keep from that idea, and what do you add so a missing auth dependency can't slip through?",
  "model": "Keep the override for tests about business logic: they shouldn't depend on login. But make it opt-in (a fixture like `as_user`), not global, and add real-token tests: login success and failure, the 401 cases (missing, garbage, expired, deleted user) for get_current_user, and a parametrized test over every protected route that a request without a token gets 401. That last test catches an endpoint that forgot Depends(get_current_user), which overridden tests can never see.",
  "explanation": "Overrides for speed and focus; a route-wide 401 check for coverage." }
```

## 5. Your turn

Implement the form-based login endpoint and `get_current_user` for the chat API. `security.py` already has hashing and tokens. The tests cover every 401 path and the timing rule.

```exercise
WEB.M06.L03.E1
```
