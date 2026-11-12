# PRJ-03: Mini messenger REST API

Starts after WEB.M06. Estimated 25 h. Draft spec, to be confirmed with the learner when WEB.M06 is done.

1. **Problem:** build a small messenger HTTP API with FastAPI and SQLAlchemy.
   - It covers users with password login, chats with an owner and members, and messages with cursor pagination.
   - The database schema is managed by Alembic migrations.
   - The focus is correct status codes and authorization: who may see or change what, and proving it with tests.
   - Rule: the learner writes all the code and tests. The mentor challenges the design and reviews only after an
     attempt.
2. **Functional requirements:**
   - **Fixed contract:** the mentor acceptance suite depends on these paths and status codes. Bodies are JSON.
   - **Status-code policy:**
     - A missing or invalid token gets 401.
     - A user who isn't a member gets **404** for a chat and anything inside it, so a chat's existence isn't revealed.
     - A member who lacks the required role gets **403**.
     - Validation errors get 422.
   - **Users and auth:**
     - `POST /users` `{"username", "password"}`:
       - 201 returns `{"id", "username"}`.
       - 409 if the username is taken (unique ignoring case).
       - 422 if the username is not 3–32 characters or the password is under 8 characters.
     - `POST /auth/token` `{"username", "password"}`:
       - 200 returns `{"access_token", "token_type": "bearer"}`.
       - 401 for an unknown user **or** a wrong password, with the same body for both.
     - `GET /users/me`: 200 or 401.
   - **Chats:**
     - `POST /chats` `{"title", "member_ids": [...]}`:
       - 201. The caller becomes the owner and a member.
       - 404 if a listed user doesn't exist.
     - `GET /chats`: the caller's chats only.
     - `GET /chats/{id}`: 200, or 404 for a non-member or a missing chat.
     - `POST /chats/{id}/members` `{"user_id"}`:
       - 201 on success.
       - 403 if the caller is a member but not the owner.
       - 404 if the chat isn't visible to the caller or the user doesn't exist.
       - 409 if the user is already a member.
     - `DELETE /chats/{id}/members/{user_id}`:
       - 204 on success.
       - The owner may remove anyone except themselves. Any member may remove themselves. Anything else is 403.
       - 404 if the target user isn't a member.
   - **Messages:**
     - `POST /chats/{id}/messages` `{"text"}`:
       - 201 on success.
       - 422 for blank or whitespace-only text, or text over 4000 characters.
       - 404 for a non-member.
     - `GET /chats/{id}/messages?limit=50&before=<message id>`:
       - Newest first. `limit` must be 1–100, otherwise 422.
       - Response shape:
         ```json
         {"items": [{"id": 42, "chat_id": 7, "author_id": 3, "text": "hi", "created_at": "2026-11-12T10:00:00Z", "edited_at": null}],
          "next_before": 41}
         ```
       - `next_before` is `null` when there are no older messages.
       - A `before` id that doesn't exist in this chat gets 422.
     - `PATCH /messages/{id}` `{"text"}`:
       - 200 on success. The author only; another member gets 403. Sets `edited_at`.
       - 422 for the same text rules as sending.
       - 404 if the message doesn't exist or the caller isn't a member of its chat.
     - `DELETE /messages/{id}`:
       - 204 on success. The author or the chat owner; another member gets 403.
   - **Errors:**
     - Every error body uses one documented format of your choice.
     - Validation errors (422) use the same format.
     - The README shows that format.
3. **Non-functional:**
   - **Stack:** FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PyJWT, pytest with `TestClient`, all installed in the
     project venv.
     - Use sync (`def`) endpoints and a sync `Session` here. PRJ-04 converts them to async after Course AS.
   - **Database:** SQLite, as a file in development and an isolated database per test.
     - The schema comes **only** from Alembic migrations. `create_all` is allowed in tests only if a test also checks
       that the migrations produce the same tables.
   - **One transaction per request (unit of work):**
     - Sessions come from a `yield` dependency (PY.M07, WEB.M05).
     - A failing request commits nothing.
     - No session is leaked.
   - **Config:**
     - The secret key, token lifetime and database URL come from environment variables (OPS-style config), with
       safe test values set in the tests.
     - There is no secret in the repo.
   - **Structure:** routers → services → repositories (WEB.M03). Endpoint functions contain no SQL.
   - **Code quality:** clean under Ruff (PY.M06). Type hints on the service layer.
   - **Environment:** everything runs on this machine. Nothing needs installing.
     - For password hashing, stdlib `hashlib.scrypt` works here (checked 2026-11-12).
     - bcrypt and argon2 libraries are **not** installed; adding one is a dependency change that needs approval.
4. **Architecture:**
   - **Before coding**, the learner writes a one-page `DESIGN.md`:
     - **Data model:** tables, keys, constraints. Reuse what you learned in PRJ-02; don't copy its code blindly.
     - **Layers:** which layer owns the transaction, and why.
     - **Authorization:** where membership and role checks live, so that no endpoint can forget them.
     - **Token:** what the token contains, how long it lives, and what happens when it expires.
     - **Pagination:** why a cursor (`before`) and not `offset`. Name one bug that `offset` causes when new
       messages arrive.
   - **Questions the mentor will ask:**
     - Why 404 and not 403 for non-members? When would you choose 403 instead?
     - Where do you check authorization: in the router, a dependency or the service? What happens when a second
       endpoint is added in a hurry?
     - A user is deleted while their token is still valid. What should happen, and does your code do it?
     - Which of your endpoints are idempotent? Which should be, and which can't be?
5. **Milestones:**
   - Each milestone ends when its "done" checks are met **and** `pytest` and `ruff check` are green.
   - Hours are estimates (25 h in total).
   - **M0 design (2 h).** Done when:
     - `DESIGN.md` is written and reviewed.
     - The challenge questions are answered.
   - **M1 skeleton (3 h).** Done when:
     - App factory, settings from the environment, a session dependency and an initial Alembic migration exist.
     - `GET /health` works.
     - A test runs `alembic upgrade head` on an empty database, and the expected tables exist.
   - **M2 users and auth (5 h).** Done when:
     - Register, login and `/users/me` work.
     - Passwords are hashed with a per-user random salt.
     - There are tests for:
       - a duplicate username, including a case-only difference
       - the same 401 body for an unknown user and a wrong password
       - a missing token, a malformed token, a tampered signature and an expired token
     - Make the token lifetime configurable rather than sleeping in tests.
   - **M3 chats and membership (5 h).** Done when every chat endpoint is tested for:
     - success, 401, 403, 404 and 409
     - a non-owner trying to add a member
     - the owner trying to remove themselves
   - **M4 messages and pagination (5 h).** Done when:
     - Sending and listing work.
     - Pagination is tested for:
       - an empty chat
       - exactly `limit` messages
       - `limit + 1` messages
       - walking every page with `next_before` until `null`, with no duplicates and no gaps
       - `limit` 0 and 101 (422)
       - a non-member (404)
   - **M5 second migration and editing (2.5 h).** Done when:
     - A **new** migration adds `edited_at`.
     - `PATCH` and `DELETE /messages/{id}` work, with 403 tests.
     - A test runs upgrade, downgrade one step, then upgrade again on a database that has rows.
     - Find out in the Alembic docs how it handles `ALTER` on SQLite, and write in `DESIGN.md` what you chose.
   - **M6 hardening and final review (2.5 h).** Done when:
     - The security checklist (§7) has been walked through and fixed where needed.
     - The mentor acceptance suite has been run.
     - The review is done and evidence is recorded.
6. **Testing:**
   - **Order:** write tests before each milestone's code. Use `TestClient`. Each test gets its own database.
     - Find out how to share one in-memory SQLite database across connections, or use a temp file, and justify
       your choice.
   - **Required matrix:** every endpoint has tests for:
     - the success path
     - 401
     - 403 where a role applies
     - 404, including the non-member case
     - 409 where it applies
     - 422
   - **Transaction test:**
     - Make a request fail after its first write, for example with a dependency override that raises.
     - Assert that nothing from it is in the database.
   - **Evidence:**
     - Run `pytest --junitxml=result.xml` locally and bring the report to review.
     - The site doesn't import project reports; the mentor records the result.
7. **Security:**
   - **Passwords:**
     - Use `hashlib.scrypt` with a random salt from `secrets`, and compare hashes with `hmac.compare_digest`.
     - A password or its hash never appears in a response, a log line or an error.
   - **Tokens:**
     - Signed with a secret taken from the environment.
     - The accepted algorithm is pinned when decoding.
     - The token has an expiry, and an expired token gets 401.
   - **Access control and IDOR:**
     - Every chat and message read or write checks membership or role on the server.
     - The 404/403 tests in §6 are **must-pass**.
   - **Mass assignment:** request models don't accept `id`, `owner_id`, `author_id` or `created_at`. Response models
     never include `password_hash`.
   - **User enumeration:** login gives the same 401 body for an unknown user and a wrong password.
   - **SQL injection:** use ORM queries. Any `text()` SQL uses bound parameters only.
   - **Known gap, out of scope:** rate limiting on login. Say in the review how you'd add it.
8. **Rubric (100 points):**
   - Correctness on the mentor acceptance suite: 30. The suite is written against the contract in §2 and run at M6.
   - Authentication and authorization (hashing, tokens, IDOR checks, enumeration): 20
   - Learner's tests (the full status matrix, pagination edges, transaction test): 15
   - Design and layering (no SQL in routers, one transaction per request, `DESIGN.md` defended): 15
   - Migrations (schema only from Alembic, reversible second migration, tested): 10
   - Error handling and clarity (one error format, Ruff clean, readable): 10
   - **Pass** = all of the following:
     - 70 or more
     - all core acceptance tests pass
     - every IDOR/401 must-pass test passes
     - no password hash in any response
9. **Final review:**
   - Code review in mentor review mode, covering correctness, readability, error handling, security, testing and
     architecture.
   - The learner writes a self-review: the 3 riskiest places in the code, and why.
   - **Evidence that counts:**
     - your tests passing locally (the JUnit report)
     - the acceptance suite run in the session
     - your defence of `DESIGN.md`
   - Code written with AI help doesn't count.
   - The mentor records the results in `ASSESSMENT_HISTORY.md` and `content/learner/assessments.json`. The record
     covers FastAPI, auth, API testing and migrations, rated on dimensions B, C and D.
