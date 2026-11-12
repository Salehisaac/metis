# PRJ-04: Production-style messenger

Starts after AS.M03, ARCH.M03 and OPS.M03. Estimated 25 h. Draft spec, to be confirmed with the learner when those
modules are done.

1. **Problem:** turn your PRJ-03 messenger into a service that runs the way production services do:
   - async endpoints with an async database session
   - a Redis cache with correct invalidation
   - a background worker that sends "new message" notifications
   - everything started with Docker Compose and checked by CI on every push

   Start from your reviewed PRJ-03 code. Fix any open PRJ-03 review findings first.
   - Rule: the learner writes all the code, config and tests. The mentor challenges the decisions and reviews only
     after an attempt.
2. **Functional requirements:**
   - **The PRJ-03 contract is unchanged:** every PRJ-03 path, status code and the 404/403 policy still hold. The
     PRJ-03 acceptance suite must still pass.
   - **Async API:**
     - All endpoints are `async def` and use an async SQLAlchemy session.
     - No blocking call runs on the event loop. Password hashing is CPU-bound: decide how to keep it off the loop,
       and defend the choice.
   - **Cache:**
     - Cache-aside for at least two reads: `GET /chats` (per user) and the first page of `GET /chats/{id}/messages`.
     - Every write that changes a cached result invalidates it:
       - a new message
       - an edit or delete
       - a member added or removed
       - a user deleted, if you support that
     - Each cached value has a TTL as a safety net. The TTL is not the invalidation strategy.
   - **Notifications:**
     - When a message is sent, every other member gets a notification. The API only **enqueues** a job; a separate
       worker process delivers it.
     - "Deliver" means writing a row that `GET /users/me/notifications` returns (newest first, paginated like
       messages).
     - The worker:
       - retries a failed job up to 3 times with a delay
       - moves a job that still fails to a dead-letter list
       - is idempotent: processing the same job twice creates no duplicate notification
   - **Health:**
     - `GET /health` reports whether the database and Redis are reachable.
     - If Redis is down, reads still work from the database (degraded, not failing). Sending still works, and the
       README states what happens to its notification.
3. **Non-functional:**
   - **Stack:** FastAPI, SQLAlchemy async, the `redis` client library (asyncio API), pytest with AnyIO
     (`@pytest.mark.anyio`), Ruff.
   - **Config:** all of it through environment variables. Keep a committed `.env.example` and an ignored `.env`.
   - **Logs:** structured log lines (OPS.M02) for each request and each job attempt, with no message text and no
     secrets.
   - **Environment:** this needs your decision before M4. What's installed now (checked 2026-11-12):
     - **Not installed:** Docker, Docker Compose, PostgreSQL, a Redis server, and any PostgreSQL driver (no
       `psycopg` or `asyncpg`).
     - **Installed in the venv:** `redis` 8.1.0 (client only), `fakeredis` 2.40.0, `aiosqlite` 0.22.1.
       `fakeredis.FakeAsyncRedis` was run here, including a blocking list pop.
     - **To install, if you agree:**
       - Docker Engine with the Compose plugin, on your machine. OPS.M01 and DB.M08 need it too, so you may have
         decided already.
       - PostgreSQL and Redis then run **as Compose services**, not on the host.
       - An async PostgreSQL driver goes into the app image's requirements. Choosing it is a dependency decision you
         explain in review.
     - **Local fallback** (no Docker): aiosqlite instead of PostgreSQL and fakeredis instead of Redis. M0–M3 and M5
       need nothing else. Each milestone below is marked **[fallback OK]** or **[needs Docker]**.
4. **Architecture:**
   - **Before coding**, write `DESIGN.md` (one page) about **what changes** from PRJ-03:
     - **Cache table:** each key pattern, its value, its TTL, and every write that invalidates it.
     - **Job format:** the payload as JSON, its idempotency key, and the retry and dead-letter rules.
     - **Failure table:** what happens to a request and to a notification when each of these is down: Redis, the
       database, the worker.
     - **Process diagram:** api, worker, postgres and redis, as boxes and arrows.
   - **Questions the mentor will ask:**
     - Do you invalidate the cache before or after the database commit? Draw the interleaving that serves stale data
       for each choice.
     - Why a separate worker process and not FastAPI's `BackgroundTasks`? Find out from the FastAPI docs when
       `BackgroundTasks` run and in which process, then argue it.
     - The API commits the message, then crashes before enqueuing the job. Is the notification lost? What would
       prevent that, and is it worth it here?
     - Which of your cache keys could leak one user's data to another?
5. **Milestones:**
   - Each milestone ends when its "done" checks are met **and** `pytest` and `ruff check` are green.
   - Hours are estimates (25 h in total).
   - **M0 design delta (2 h) [fallback OK].** Done when:
     - `DESIGN.md` is reviewed.
     - The challenge questions are answered.
     - The Docker decision is made, or postponed explicitly with M4 at risk.
   - **M1 async conversion (5 h) [fallback OK: aiosqlite].** Done when:
     - All endpoints are async and the PRJ-03 suite passes against the async app.
     - **Event-loop checkpoint:**
       - Write a small experiment in which a blocking call (for example `time.sleep`) inside an `async def`
         endpoint makes concurrent requests take turns. Fix it, measure both, and keep the numbers in the README.
       - Explain in 3–5 sentences what `await` does and why the experiment proves it doesn't start a thread. This
         corrects the Q-round answer.
   - **M2 cache (4 h) [fallback OK: fakeredis].** Done when cache-aside works, with tests that:
     - assert a hit after a miss
     - assert the cache is invalidated by each write in §2
     - prove one user never receives another user's cached chat list
     - show the API still answering correctly when the Redis client raises connection errors
   - **M3 worker (5 h) [fallback OK: fakeredis].** Done when:
     - Enqueue, a worker loop, retries, dead-letter and idempotency all work.
     - The worker's "process one job" step is a function that tests call directly.
     - There are tests for:
       - success
       - failure then success on retry
       - permanent failure reaching the dead-letter list
       - the same job processed twice (no duplicate)
       - a malformed job payload (dead-lettered and logged, no crash)
   - **M4 Docker and Compose (4 h).** **[needs Docker]** for the run; static checks are [fallback OK].
     - A `Dockerfile` that runs as a non-root user, with a `.dockerignore`.
     - A Compose file with `api`, `worker`, `postgres` and `redis`, health checks, and config from `.env`.
     - Done when:
       - Static tests parse the compose YAML with PyYAML and assert your rules: services present, no secret values
         inline, `redis` and `postgres` not published to host ports.
       - **And** `docker compose up` brings the stack up, a message sent through the API produces a notification
         through the real worker and Redis, and you show it live in review.
   - **M5 CI (2 h) [fallback OK].** Done when:
     - The pipeline, on the CI you chose in OPS.M03, runs `ruff check` and `pytest` on every push, using aiosqlite
       and fakeredis so it needs no services.
     - A deliberately broken commit turns it red.
   - **M6 final review (3 h).** Done when:
     - The acceptance suites have been run.
     - The live Compose demo is done.
     - The review and self-review are done and evidence is recorded.
     - If Docker was declined, M4's live part is marked "Not assessed", the project can't pass, and scope changes
       need the learner's and mentor's agreement.
6. **Testing:**
   - **Order:** write tests before each milestone's code. Async tests use AnyIO's plugin; don't add pytest-asyncio.
   - **Isolation:**
     - Each test gets its own database and a fresh `FakeAsyncRedis`.
     - Inject both through dependencies, so tests never reach a real server by accident.
   - **Required tests:** the cache invalidation and cross-user tests (M2), the worker reliability tests (M3), and the
     static compose tests (M4).
   - **Known limits of the fallback:** fakeredis and SQLite are not the real servers. Timing, locking and some
     command details differ, so the M4 live run is the integration evidence.
   - **Evidence:**
     - Run `pytest --junitxml=result.xml` locally, and bring a CI run link or log.
     - The mentor records the results; the site doesn't import project reports.
7. **Security:**
   - **Secrets:**
     - No secrets in the repo, the image or CI logs.
     - `.env` is git-ignored and excluded by `.dockerignore`.
     - CI uses test-only values.
   - **Network exposure:** Redis and PostgreSQL are reachable only on the Compose network, not published on host
     ports. Only `api` exposes a port.
   - **Containers:** run as a non-root user. Pin base image tags; no `latest`.
   - **Cache authorization:**
     - Keys include the user (or check membership before serving).
     - A cached response must never bypass the PRJ-03 access rules. The cross-user cache test is **must-pass**.
   - **Untrusted job payloads:**
     - Jobs are JSON, never `pickle`.
     - The worker validates each payload and re-checks that the recipient is still a member before delivering.
   - **Logs:** never log tokens, password material or message text.
8. **Rubric (100 points):**
   - Correctness: PRJ-03 acceptance suite plus the PRJ-04 suite (notifications, health): 25
   - Cache correctness (cache-aside, invalidation on every write, degraded mode): 15
   - Worker reliability (retries, dead-letter, idempotency, malformed jobs): 15
   - Docker and Compose (Dockerfile, health checks, config, live demo): 15
   - CI (Ruff and pytest on push, proven red on a broken commit): 10
   - Learner's tests: 10
   - Async correctness and the event-loop checkpoint: 10
   - **Pass** = all of the following:
     - 70 or more
     - all core acceptance tests pass
     - the cross-user cache test passes
     - no secrets in the repo or the image
     - the live Compose demo is done
     - the `await` explanation is correct in review
9. **Final review:**
   - Code and config review in mentor review mode, including a walkthrough of one request and one job from start to
     finish.
   - The learner writes a self-review: the failure you'd fear most in production, and how you'd notice it.
   - **Evidence that counts:**
     - your tests passing locally (the JUnit report)
     - a passing CI run
     - the live Compose demo
     - the acceptance suites run in the session
     - your answers to the challenge questions
   - Code written with AI help doesn't count.
   - The mentor records the results in `ASSESSMENT_HISTORY.md` and `content/learner/assessments.json`. The record
     covers async, caching, background work, Docker and CI.
