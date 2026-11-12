---
{
  "id": "WEB.M06.L04",
  "title": "Authorization: roles, ownership, 401 vs 403",
  "difficulty": "intermediate",
  "minutes": 90,
  "prerequisites": ["WEB.M06.L03"],
  "objectives": [
    "Distinguish 401 (identity not established) from 403 (identity known, action not allowed), and decide when 404 is the better answer",
    "Implement role checks as a reusable dependency factory, on a route or on a whole router",
    "Implement object-level checks (membership, ownership) inside the endpoint, on every request, and recognise an IDOR",
    "Test authorization as a grid of callers × endpoints, with allowed and denied rows, plus a route-wide 401 check"
  ],
  "why": "The admin panel you worked on had login, but no authorization: any operator could ban any account. That's the most common kind of access-control bug. Authentication works, everyone who logs in is a real employee, and nobody asks 'may this person do this, to this account?'. It also never shows up in a demo, because the demo user is allowed everything. This lesson is about asking that question in every endpoint, and proving with tests that the answer is right.",
  "applications": [
    "Moderator and admin actions (ban, delete, pin) in the chat API",
    "Members-only resources: a chat's messages, files and member list",
    "Ownership rules: only the author edits a message, only the owner renames a chat"
  ],
  "exercises": ["WEB.M06.L04.E1", "WEB.M06.L04.E2"],
  "sources": [
    {
      "title": "OWASP REST Security Cheat Sheet",
      "url": "https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html",
      "version": "OWASP Cheat Sheet Series (current)",
      "verified": "2026-11-12",
      "claims": [
        "401 Unauthorized: wrong or no authentication provided",
        "403 Forbidden: authentication succeeded but the authenticated user doesn't have permission to the requested resource",
        "Non-public REST services must perform access control at each API endpoint"
      ]
    },
    {
      "title": "OWASP Authorization Cheat Sheet",
      "url": "https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html",
      "version": "OWASP Cheat Sheet Series (current)",
      "verified": "2026-11-12",
      "claims": [
        "Enforce least privilege and deny by default",
        "Validate permissions on every request, server-side, for the specific object being accessed",
        "Changing an identifier must not grant access to the object (insecure direct object reference, IDOR); lookup IDs must not be accessible even when guessed",
        "Prefer attribute- and relationship-based access control over RBAC",
        "Create unit and integration tests for authorization logic; handle failed access-control checks no matter how unlikely"
      ]
    },
    {
      "title": "FastAPI Advanced: Testing Dependencies with Overrides",
      "url": "https://fastapi.tiangolo.com/advanced/testing-dependencies/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["A dependency can be used in a path operation, a path operation decorator or an include_router() call"]
    },
    {
      "title": "FastAPI Tutorial: Simple OAuth2 with Password and Bearer",
      "url": "https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["Dependencies build on each other: get_current_active_user depends on get_current_user and adds a rule"]
    }
  ]
}
---
## 1. Who are you, and may you?

| Status | Question that failed | Example |
|---|---|---|
| **401 Unauthorized** | *Who are you?* No token, a broken or expired token, a deleted account | `POST /admin/users/7/ban` without a header |
| **403 Forbidden** | *May you do this?* The identity is known; the action isn't allowed | an ordinary user calling the ban endpoint |
| **404 Not Found** | *Should you even know this exists?* | an outsider asking for chat 12's messages |

The OWASP REST Security Cheat Sheet defines 401 as "wrong or no authentication" and 403 as "authenticated, but no permission". The names are confusing ("Unauthorized" really means *unauthenticated*), so learn them by the question.

**When 404 beats 403:** if a 403 would confirm that something exists ("chat 12 exists, you're just not in it"), an outsider can probe ids. Answer exactly as you would for an id that doesn't exist. Use 403 when the caller may already know the object exists, for example a member trying to delete someone else's message in a chat they can read.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Sara is a member of chat 1 and sends a valid token with `DELETE /chats/1/messages/5`. Message 5 is Ali's. Only authors and admins may delete. What should she get?",
  "options": ["403: she's authenticated and can see the message, but may not delete it", "401: she isn't allowed", "404: hide the message", "200 with an error in the body"], "answer": 0,
  "explanation": "Her identity is established, so it's not 401. She can already read message 5 in chat 1, so hiding it with 404 protects nothing. 403 is honest here." }
```

## 2. Role checks as a dependency

A role check can be decided before the endpoint body runs: it needs only the current user. That makes it a dependency, and because you want to pass the allowed roles, a **dependency factory**: a function that returns the dependency. Here's the pattern for paid plans (exporting chat history needs pro or team):

```python
def requires_plan(*plans: str):
    def check(account: Annotated[Account, Depends(current_account)]) -> Account:
        if account.plan not in plans:
            raise HTTPException(status_code=403, detail="Upgrade required")
        return account
    return check


@app.get("/chats/{chat_id}/export")
def export_history(chat_id: int, account: Annotated[Account, Depends(requires_plan("pro", "team"))]):
    return {"chat_id": chat_id, "by": account.id}


billing = APIRouter(prefix="/billing")
# ... routes on billing ...
app.include_router(billing, dependencies=[Depends(requires_plan("team"))])
```

```console
$ # no token / free plan / pro plan, against /chats/1/export and /billing/invoices
None 401 401
tok-free 403 403
tok-pro 200 403
```

- `check` depends on `current_account`, so **401 comes first**: without an identity, the plan question never runs. This is the stacking from lesson 3.
- **Deny by default.** `not in plans` rejects every value you didn't list: a typo, a new plan, `None`. Writing `if account.plan == "free": raise ...` instead would let a future `"trial"` plan straight through.
- **On a whole router.** `include_router(..., dependencies=[...])` protects every route in it, including ones added later. That's the safer default for an `/admin` router.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "from typing import Annotated\nfrom fastapi import Depends, FastAPI, Header, HTTPException\nfrom fastapi.testclient import TestClient\n\nROLES = {\"t1\": \"user\", \"t2\": \"moderator\", \"t3\": \"auditor\"}\n\ndef current_role(authorization: Annotated[str | None, Header()] = None) -> str:\n    role = ROLES.get((authorization or \"\").removeprefix(\"Bearer \"))\n    if role is None:\n        raise HTTPException(status_code=401)\n    return role\n\ndef deny_users(role: Annotated[str, Depends(current_role)]) -> str:\n    if role == \"user\":\n        raise HTTPException(status_code=403)\n    return role\n\napp = FastAPI()\n\n@app.post(\"/admin/purge\")\ndef purge(role: Annotated[str, Depends(deny_users)]):\n    return role\n\nclient = TestClient(app)\nfor t in (\"t1\", \"t2\", \"t3\", \"nope\"):\n    print(client.post(\"/admin/purge\", headers={\"Authorization\": f\"Bearer {t}\"}).status_code)",
  "answer": "403\n200\n200\n401",
  "explanation": "deny_users blocks only the role it names. The auditor, a role nobody thought about, is let into a destructive admin endpoint. An allow-list (`if role not in (\"moderator\", \"admin\")`) would have denied it by default. Unknown tokens never reach the role check: 401." }
```

## 3. Object-level checks: the IDOR

Roles answer "may this *kind* of user call this endpoint?". Most real rules are about **this specific object**: is the user a member of *this* chat, the author of *this* message, allowed to ban *this* account? These checks need the object, so they live in the endpoint (or a helper it calls), after loading it.

Forgetting them is so common it has a name: **IDOR**, insecure direct object reference. Change the id in the URL and you get someone else's data:

```python
MEMBERS = {1: {10, 11}}  # chat 1: users 10 and 11


@app.get("/chats/{chat_id}/pins")
def pins(chat_id: int, user_id: Annotated[int, Depends(current_user_id)]):
    if chat_id not in MEMBERS:
        raise HTTPException(status_code=404, detail="chat not found")
    return ["release at 5pm"]
```

```console
$ # GET /chats/1/pins as user 10 (member), then as user 99 (not a member)
200 200
```

User 99 is authenticated, so the endpoint "works". The fix is one more condition, `user_id not in MEMBERS[chat_id]`, in the same 404 branch, so outsiders can't tell a hidden chat from a missing one. Put that rule in **one helper** that every chat endpoint calls ("load the chat or 404"), so the rule can't drift between endpoints.

The OWASP Authorization Cheat Sheet's rules for this:

- Check permissions on **every request**, for the **specific object**.
- **Server-side.** Hiding the "Ban" button in the UI is not access control: anyone can send the request with curl.
- Unguessable ids (UUIDs) are fine, but **never a substitute** for the check.
- **Deny by default**, and handle every failed check, however unlikely it seems.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "If the frontend only shows the Ban button to moderators, the ban endpoint only needs to check that the caller is logged in.", "answer": false,
  "explanation": "Access control must be enforced server-side on every request. Anyone can call the API directly with a valid token. That was exactly the admin-panel bug: any logged-in operator could ban." }
```

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "`GET /chats/{chat_id}/files` checks the token and then returns `files_for(chat_id)`. What's the vulnerability, and the fix?",
  "options": ["IDOR: any logged-in user can read any chat's files by changing chat_id; check membership for that chat_id and answer 404 to outsiders", "Missing 401: add OAuth2PasswordBearer", "SQL injection through chat_id", "None: chat ids are integers, so they're validated"], "answer": 0,
  "explanation": "Authentication is there; the object-level check is missing. Validation only checks the id's type, not whether this user may access this chat." }
```

**Where do roles come from?** Read them from your database on each request (as the exercise's `get_current_user` does), not only from a claim in the token. A role inside a token stays valid until the token expires, even after you demote or ban the user. Short token lifetimes keep that window small if you do put roles in tokens.

## 4. Testing authorization: a grid

Authorization bugs go **both ways**: too permissive is a security hole, too strict is an outage for your admins. So test the full grid of callers × endpoints, with allowed and denied cells:

| | anonymous | bad token | outsider | member | owner/author | admin |
|---|---|---|---|---|---|---|
| list messages | 401 | 401 | 404 | 200 | 200 | 200 |
| delete a message | 401 | 401 | 404 | 403 | 204 | 204 |
| ban a user | 401 | 401 | 403 | 403 | 403 | 200 |

Each cell is one parametrized row (WEB.M04.L03). Two details:

- **"Anonymous" and "bad token" are different rows.** A missing header is rejected by `OAuth2PasswordBearer`; a garbage token reaches your `get_current_user`. A bug in one isn't visible through the other.
- **Add a route-wide check** that every non-public route answers 401 without a token. It catches the endpoint someone added without the dependency, which no per-endpoint grid will ever cover:

```python
PUBLIC = {"/health"}
client = TestClient(app)
for route in app.routes:
    if isinstance(route, APIRoute) and route.path not in PUBLIC:
        for method in route.methods:
            url = route.path.replace("{chat_id}", "1")
            status = client.request(method, url).status_code
            if status != 401:
                print("UNPROTECTED:", method, route.path, status)
```

```console
UNPROTECTED: DELETE /chats/{chat_id} 200
```

In a real test, collect the unprotected routes in a list and `assert not unprotected`.

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "A test table for `PATCH /chats/{id}` (owner or admin may rename) has rows for anonymous (401), outsider (404) and member (403). Which bug can it NOT catch?",
  "options": ["Admins get 403 because the check only allows the owner", "Members can rename", "Outsiders get 403 instead of 404", "Anonymous callers get 200"], "answer": 0,
  "explanation": "The table has only denied rows. A check that's too strict (rejecting admins) passes all of them. Add allowed rows: owner → 200, admin → 200." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Redesign the ban endpoint of the admin panel where any operator could ban. Describe the rules you would enforce (who may ban whom), where each check lives in FastAPI, and the rows of the test grid.",
  "model": "Rules: only moderators and admins may ban (role allow-list, deny by default); moderators may ban only ordinary users; admins may ban anyone except themselves; banned accounts are rejected at authentication. Placement: a require_role(\"moderator\", \"admin\") dependency factory on the route (or on the whole /admin router); the target-dependent rules inside the endpoint after loading the target (404 if missing); get_current_user rejects banned users with 401. Grid: anonymous 401, bad token 401, user 403, moderator→user 200, moderator→moderator 403, moderator→admin 403, admin→moderator 200, admin→self 403, admin→unknown 404; plus 'banned user is locked out' and a route-wide 401 check for /admin.",
  "explanation": "A role dependency for 'who may call', object rules in the endpoint for 'to whom', and a grid with allowed and denied rows." }
```

## 5. Your turn

Two exercises:

1. **E1 (implement):** the moderation endpoints authenticate but don't authorize. Add `require_role`, the ban rules and the chat and message checks.
2. **E2 (test):** a correct chat-settings app. Write its access grid and kill seven mutants, including one that only a bad-token row can catch.

```exercise
WEB.M06.L04.E1
```

```exercise
WEB.M06.L04.E2
```
