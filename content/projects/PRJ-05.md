# PRJ-05: Capstone: a system you design

Starts after ARCH.M04 and DB.M08. Estimated 30 h. Draft spec, to be confirmed with the learner when those modules
are done.

1. **Problem:** you design a backend system from scratch and then build it.
   - Pick **one** of the candidate problems below, or propose your own of similar size. The mentor must approve it
     at M1, and it can't be about messaging.
   - Each candidate has one **core invariant** that must hold under concurrent requests. That invariant is the
     centre of the design.
   - **A. Room and equipment booking:**
     - Users book a resource for a time range, cancel, and list their bookings.
     - Admins manage resources and opening hours.
     - **Invariant:** two confirmed bookings of the same resource never overlap, even when two requests arrive at
       the same moment.
     - Things to decide: time zones, half-open ranges, cancellation rules.
   - **B. Inventory with stock reservations:**
     - Products have stock. A checkout reserves items for a limited time, then confirms or releases them. An expired
       reservation returns its stock automatically.
     - **Invariant:** stock is never sold below zero (no overselling), and creating an order is idempotent under
       client retries.
   - **C. Shared-expense ledger:**
     - Groups of users record expenses split between members, see balances, and record settle-up payments.
     - **Invariant:** each group's balances always sum to exactly zero. Ledger entries are append-only; corrections
       are new entries. Money is never stored as a float.
   - **Rule:** the learner writes the design and all the code. The mentor challenges the design and reviews only
     after an attempt. No design or implementation is supplied.
2. **Functional requirements:** these hold whichever problem you choose; your design doc adds the problem-specific
   ones.
   - An HTTP API with at least 4 resources and authentication, plus at least 2 roles with different permissions.
   - The core invariant is enforced so that **concurrent** requests can't break it. The design doc says whether a
     database constraint, a lock, an isolation level or a combination enforces it, and why.
   - At least one background job that fits the problem: booking reminders, releasing expired reservations, or a
     periodic balance check. Retries are safe because the job is idempotent.
   - At least one list endpoint with cursor pagination and filters.
   - Errors use one documented format. Status codes follow the PRJ-03 policy, and the design doc justifies any
     change.
3. **Non-functional:**
   - **Stack:** FastAPI (async), SQLAlchemy, Alembic, **PostgreSQL** as the real database, Redis only if your design
     justifies it, Docker Compose, CI.
   - **Measurable targets:** the design doc states its own (for example "p95 of `POST /bookings` under X ms with N
     concurrent clients on my machine"). You measure at least one and report the real numbers, met or not.
   - **Code quality:** clean under Ruff, type hints on the service layer, and config only from the environment.
   - **Environment:** this needs your decision before M2. What's installed now (checked 2026-11-12):
     - **Not installed:** Docker, Docker Compose, PostgreSQL, a Redis server, and any PostgreSQL driver.
     - **To install:**
       - Docker Engine with the Compose plugin. You need it for DB.M08 anyway.
       - PostgreSQL then runs as a Compose service.
       - A PostgreSQL driver goes into the project's requirements (the image, and the host venv if your tests run on
         the host). That is a dependency decision you justify.
     - **Local fallback:** unit and most API tests may run on SQLite (aiosqlite) and fakeredis, for speed and for
       CI.
     - **Needs the real PostgreSQL:**
       - the concurrency test of the core invariant
       - migrations
       - any PostgreSQL behaviour you rely on, such as exclusion constraints, row locks, isolation levels, or JSONB
         operators and indexes
       - Note that this machine's SQLite (3.45.1) also accepts `RETURNING` and has a `jsonb()` function (checked
         2026-11-12), so "it ran on SQLite" doesn't show PostgreSQL behaviour.

       SQLite's locking differs from PostgreSQL's (DB.M06), so a concurrency test that passes on SQLite proves
       nothing here.
4. **Architecture:**
   - **The design doc comes first.** No code before it is approved at M1.
   - `DESIGN.md` is about 2 pages, with these fixed sections:
     1. Problem and scope: what's in, and what's explicitly out.
     2. Requirements: functional, and non-functional with numbers.
     3. Data model: tables, keys and constraints, with one sentence of "why" per constraint.
     4. API: an endpoint table with method, path, purpose, success code and error codes, plus 2 example
        request/response pairs.
     5. Core invariant: how it's enforced, and the race you're preventing, drawn as two interleaved requests.
     6. Trade-offs: at least 3 decisions, each with the alternative you rejected and why.
     7. Failure modes: database down, Redis down if used, the worker crashing mid-job, a client retrying.
     8. Test plan: what's tested at each level, and what runs against the real PostgreSQL.
     9. Security: a threat list (who, what, how) with your mitigation for each.
   - **Defence:** in a review session the mentor asks challenge questions, for example:
     - What happens with two identical requests 1 ms apart?
     - Why this isolation level?
     - What does a retry after a timeout do?
     - Which constraint would you drop first under load?

     You answer, then revise the doc. Approval is recorded with the date.
5. **Milestones:**
   - Each milestone ends when its "done" checks are met **and** `pytest` and `ruff check` are green.
   - Hours are estimates (30 h in total).
   - **M0 choice and design doc v1 (4 h) [no tools needed].** Done when the problem is chosen and all 9 sections of
     `DESIGN.md` are written.
   - **M1 design defence (2 h).** Done when:
     - The challenge questions are answered and the doc is revised.
     - The mentor has written the acceptance suite against the approved API.
     - The approval date is recorded.
     - The Docker decision is made.
   - **M2 skeleton (4 h) [needs Docker for PostgreSQL].** Done when:
     - The Compose file runs `postgres` (plus `api`, and `redis` if used).
     - Alembic migrations run on PostgreSQL from empty to head and back down.
     - Settings come from the environment.
     - CI runs Ruff and pytest.
   - **M3 core domain and API (8 h) [fallback OK for most tests].** Done when:
     - The endpoints from the approved design work.
     - The full status-code matrix is tested (success, 401, 403, 404, 409, 422 where they apply).
     - Pagination edge cases are tested.
   - **M4 invariant under concurrency (4 h) [needs PostgreSQL].** Done when:
     - A test fires concurrent requests or transactions that would break the invariant without your mechanism, and
       it passes against PostgreSQL.
     - You show it **failing** with the mechanism switched off, which proves the test can catch the race.
   - **M5 background job (3 h) [fallback OK: fakeredis or a database-backed queue].** Done when the job works and is
     tested for success, retry, a duplicate run (idempotent) and a malformed payload.
   - **M6 security review (3 h).** Done when:
     - `SECURITY.md` walks your threat list and the checklist in §7.
     - Each finding is fixed with a test, or accepted with a written reason.
     - No critical finding is left open.
   - **M7 final review (2 h).** Done when:
     - The acceptance suite has been run and the live Compose demo is done.
     - A retrospective is written: where the built system differs from `DESIGN.md`, and why.
     - Evidence is recorded.
6. **Testing:**
   - **Order:** write tests before each milestone's code. Async tests use AnyIO's plugin.
   - **Layers:**
     - unit tests for domain rules
     - API tests with `TestClient` or an async client
     - integration tests against PostgreSQL in Compose
   - **Required:**
     - the full status-code matrix
     - pagination edges
     - the concurrency test of the invariant (M4, real PostgreSQL)
     - a migration up/down test on PostgreSQL
     - job retry and idempotency tests
     - a test for each security finding you fixed
   - **Evidence:**
     - `pytest --junitxml=result.xml` reports, one for the fallback run and one for the PostgreSQL run
     - a passing CI run
     - the mentor records the results; the site doesn't import project reports
7. **Security:** the review in M6 must cover at least:
   - **Authentication:** password hashing, token signing, expiry and a pinned algorithm.
   - **Authorization:** for every endpoint, who may call it, and an IDOR test for each resource that has an owner.
   - **Input validation:** at the API boundary, with no mass assignment.
   - **SQL:** ORM or bound parameters only.
   - **Secrets:** none in the repo, the image or CI logs. Database and Redis are not published to host ports.
     Containers run as non-root.
   - **Abuse cases specific to your problem:**
     - booking: hogging slots
     - inventory: reserving everything and never paying
     - ledger: editing history
   - **Logging:** no personal data or secrets in the logs.
8. **Rubric (100 points):** the same for every problem choice.
   - Design doc and its defence (completeness, trade-offs argued, revisions made): 20
   - Correctness on the mentor acceptance suite, written against the approved API at M1: 20
   - Core invariant under concurrency (mechanism, the failing-then-passing proof on PostgreSQL): 15
   - Learner's tests (layers, status matrix, edges, readability): 15
   - Security review and fixes (`SECURITY.md`, tests for the fixes): 10
   - Data model and migrations on PostgreSQL: 10
   - Operations (Compose, CI, config, measured target reported honestly): 5
   - Clarity (structure, naming, README): 5
   - **Pass** = all of the following:
     - 70 or more
     - all core acceptance tests pass
     - the concurrency test passes on real PostgreSQL
     - the design doc was approved before coding
     - no critical security finding is left open
9. **Final review:**
   - A final mentor review covering code, design and security, with a live demo through Compose.
   - The learner presents the retrospective: what the design got right and wrong, and what you'd do differently.
   - **Evidence that counts:**
     - the approved design doc and its revision history
     - your tests passing (the JUnit reports, fallback and PostgreSQL)
     - a passing CI run
     - the acceptance suite run in the session
     - the security review
   - Code written with AI help doesn't count.
   - The mentor records the results in `ASSESSMENT_HISTORY.md` and `content/learner/assessments.json`. The record
     covers the architecture goal (designing a system unaided) on dimensions A–D, and updates `LEARNER_PROFILE.md`
     narratively.
