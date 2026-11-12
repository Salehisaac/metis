# Curriculum Proposal: Python Backend Engineer

**Status: APPROVED at Gate 2 (2026-11-12).** Based on Assessment 1 (2026-11-12); see `LEARNER_PROFILE.md`.

## How to read this
- **Hierarchy:** Path → Course → Module → Lesson → Exercise → Assessment → Project.
- **Stable IDs:** `PY.M02`, `PY.M02.L03`, `PY.M02.L03.E1`, `PY.M02.A` (module assessment), `PRJ-01`.
  IDs are never renumbered or reused; a removed item is marked *retired*.
- **Statuses:**
  - SKIP: demonstrated mastery.
  - REVIEW: learned before, needs reinforcement.
  - LEARN: insufficient knowledge.
  - DEEPEN: basics exist, advanced knowledge missing.
  - APPLY: concept exists, practice missing.
- **SKIP list is empty.** Assessment 1 demonstrated no mastery, so nothing qualifies.
- **Not-assessed topics** (Git, Docker, SQL CRUD, auth, debugging unfamiliar code) get a **provisional status plus a placement
  check of about 5 minutes** at the start of their module. The check decides whether that module becomes SKIP, REVIEW or LEARN.
  Missing evidence is never treated as zero or as competence.
- **Lesson detail:** individual lessons are listed only for Course PY (the first course). Lessons for later courses get their
  IDs when that module starts (Phase 7), so they can adapt to how earlier modules went.
- **Every lesson:** a short "why" explanation chunk with Go comparisons, then a hands-on task with tests, repeated.
  Key details come back in later exercises, because Assessment 1 showed details need repetition.
- **Rule:** no AI on exercises or assessments. The AI mentor gives hints and explanations only after an attempt.

## Thread T1: spec to working code (runs through every module)
This is the biggest gap from Assessment 1, so it is part of every module's assessment instead of being a separate module.

Every module assessment (`*.A`) requires the learner to:
1. Restate the spec in their own words.
2. List at least 3 edge cases before coding.
3. Make the supplied tests pass. From `PY.M04` on, also write their own tests.
4. Run the code on inputs beyond the given example.

## Courses and status

| Course | Status | Why |
|---|---|---|
| **PY**: Python for Go developers | LEARN | P1/P2: Python semantics at A1; no Python written. Go background speeds this up, so no "programming from zero". |
| **DB**: Databases and SQL | LEARN (CRUD provisional) | Transactions A0 misconception; manual escaping proposed instead of placeholders; JOINs and locking self-reported weak. CRUD not assessed, so it gets a placement check. |
| **WEB**: HTTP and FastAPI | APPLY (HTTP/REST), LEARN (FastAPI) | REST semantics A2 (409, idempotency ✓). FastAPI, Pydantic and auth never used. |
| **AS**: Async Python | LEARN | Thinks `await` starts a thread (A0). Needed for async FastAPI. |
| **ARCH**: Architecture and design | APPLY | Design instincts A2 (queues, cache invalidation), but has never designed a system unaided. This is goal 2. |
| **OPS**: Production basics | LEARN (Docker provisional) | Has never written a Dockerfile, CI or production config. Docker gets a placement check. |
| Git | Provisional, placement check in `PY.M01.L04` | Strong self-report, but the history is AI-assisted. |

**Excluded (not a current goal, not SKIP):** AI engineering and agents; interview prep; advanced distributed systems;
performance engineering beyond indexes and query plans. These can be added later on request.

## Dependency map
```
PY.M01 setup+pytest ─► PY.M02 names/mutability ─► PY.M03 data structures ─► PY.M04 functions/errors/tests
                                                                                │
             ┌──────────────────────────────────┬──────────────────────────────┤
             ▼                                  ▼                              ▼
     PY.M05 classes/typing ─► PY.M06 packages  DB.M01 CRUD ─► DB.M02 modeling/JOINs ─► DB.M03 transactions
             │                     │                                                    │
             ▼                     ▼                                                    ▼
      PY.M07 generators/context managers/decorators                         DB.M04 safe SQL from Python
             │                                                                          │
             ▼                                                                          ▼
     WEB.M01 HTTP+FastAPI routing ─► WEB.M02 Pydantic ─► WEB.M03 DI/structure ─► WEB.M04 API testing
                                                                                        │
                                          DB.M07 SQLAlchemy+migrations ◄────────────────┤ (needs DB.M03)
                                                     │                                  │
                                                     ▼                                  ▼
                                          WEB.M05 DB in FastAPI ─────────────► WEB.M06 auth
                                                     │
                     AS.M01 event loop ─► AS.M02 asyncio ─► AS.M03 async FastAPI+DB
                                                     │
                     ARCH.M01 layering ─► ARCH.M02 caching ─► ARCH.M03 queues/workers ─► ARCH.M04 design from scratch
                     DB.M05 indexes ─► DB.M06 locking      OPS.M01 Docker ─► OPS.M02 config/logging ─► OPS.M03 CI
                     DB.M08 PostgreSQL (needs OPS.M01)
```
Key chains (spec §6.1):
- Functions → type hints → Pydantic → FastAPI validation.
- Async Python → asyncio → async FastAPI.
- SQL → modeling → transactions → SQLAlchemy → optimization.
- `PY.M07` (generators, context managers) → FastAPI `yield` dependencies.

## Modules (measurable outcomes and estimated hours)

### Course PY: Python for Go developers (LEARN)
| ID | Module | Outcomes: the learner can… | Est. h |
|---|---|---|---|
| PY.M01 | Setup and the feedback loop | create a venv, run scripts, run pytest and explain a failing test's output | 4 |
| PY.M02 | Names, objects, mutability | predict output for aliasing, mutation vs rebinding and copying (≥ 4/5 unseen items); explain with a diagram | 5 |
| PY.M03 | Data structures and strings | solve 3 unseen problems using slicing, dict/set, sorting with `key=` (multi-key, tie-break), and string methods | 8 |
| PY.M04 | Functions, errors, writing tests | design functions with exceptions (compared with Go errors); write parametrized pytest suites that catch a seeded bug | 6 |
| PY.M05 | Classes, dataclasses, typing | model a domain with dataclasses and type hints; choose composition vs inheritance and justify it | 8 |
| PY.M06 | Modules, packages, tooling | structure a multi-module package with `pyproject.toml`; code is clean under Ruff | 4 |
| PY.M07 | Iterators, generators, context managers, decorators | write a generator pipeline, a context manager (compared with Go `defer`) and a decorator, each with tests | 8 |

**Lessons (Course PY only):**
- **PY.M01**
  - L01 Running Python: interpreter, REPL, scripts, `python -m` (vs `go run`)
  - L02 venv and pip: why isolate dependencies
  - L03 pytest: reading a test, running it, reading a failure
  - L04 Learner workspace in Git, plus the Git placement check
- **PY.M02**
  - L01 Names are labels: `is` vs `==`
  - L02 Mutable vs immutable types
  - L03 Mutation vs rebinding across calls (Go pointer analogy; revisits P2)
  - L04 Copies (shallow vs deep) and the mutable-default-argument trap
- **PY.M03**
  - L01 Lists and slicing: end-exclusive, clamping, negative indices, step (revisits P1/P2)
  - L02 Dicts and sets: counting, grouping, `Counter`
  - L03 Tuples, unpacking, sorting with `key=` and tie-breaks (revisits I1)
  - L04 Strings: `split`/`join`/`strip`, f-strings
  - L05 Comprehensions
- **PY.M04**
  - L01 Parameters: positional, keyword, defaults, `*args`/`**kwargs`
  - L02 Exceptions vs Go error values: `raise`, `try`/`except`/`else`/`finally`
  - L03 Designing error handling: custom exceptions, where to catch
  - L04 Writing your own tests: parametrize, edge cases, testing exceptions
- **PY.M05**
  - L01 Classes vs Go structs and methods
  - L02 dataclasses
  - L03 Type hints, and `Protocol` vs Go interfaces
  - L04 Composition vs inheritance
- **PY.M06**
  - L01 Imports, modules, packages, `__main__`
  - L02 `pyproject.toml` and project layout
  - L03 Ruff
- **PY.M07**
  - L01 Iteration protocol and generators
  - L02 Context managers vs `defer`
  - L03 Closures and decorators
  - L04 `yield`-managed resources (preview of FastAPI dependencies)

### Course DB: Databases and SQL
| ID | Module | Status | Outcomes | Est. h |
|---|---|---|---|---|
| DB.M01 | SQL CRUD, filtering, grouping | provisional REVIEW (placement check) | write SELECT with WHERE, GROUP BY, ORDER BY, LIMIT and date filters unaided | 4 |
| DB.M02 | Relational modeling and JOINs | LEARN | design a normalized schema for a messaging domain; write INNER/LEFT JOIN queries; explain the result row count | 8 |
| DB.M03 | Transactions and atomicity | LEARN | explain autocommit and crash behavior (fixes the A0 misconception); wrap multi-step writes; test the rollback | 6 |
| DB.M04 | Safe SQL from Python (`sqlite3`) | LEARN | use placeholders everywhere; explain why escaping isn't enough; build a small repository layer with tests | 5 |
| DB.M05 | Indexes and query plans | LEARN | read `EXPLAIN`; add an index justified by measurement | 6 |
| DB.M06 | Locking and concurrency | LEARN | explain shared and exclusive locks and isolation levels; reproduce and fix a lost update | 6 |
| DB.M07 | SQLAlchemy and Alembic migrations | LEARN | map models, query with sessions, write reversible migrations | 10 |
| DB.M08 | PostgreSQL specifics | LEARN | run Postgres in Docker; use constraints, `RETURNING`, JSONB where justified | 5 |

### Course WEB: HTTP and FastAPI
| ID | Module | Status | Outcomes | Est. h |
|---|---|---|---|---|
| WEB.M01 | HTTP/REST in practice and FastAPI routing | APPLY / LEARN | build endpoints with correct methods, status codes and error bodies | 6 |
| WEB.M02 | Pydantic validation and error responses | LEARN | validate input and output with models; consistent 4xx error format | 6 |
| WEB.M03 | Dependency injection and app structure | LEARN | use `Depends` for config, DB session and current user; split routers and services | 6 |
| WEB.M04 | Testing APIs (TestClient) | APPLY | test normal, invalid, edge and error paths for every endpoint | 5 |
| WEB.M05 | Database in FastAPI | LEARN | one transaction per unit of work; no leaked sessions; integration tests against a test DB | 8 |
| WEB.M06 | Authentication and authorization | LEARN (placement check) | password hashing, token auth, role checks, with tests for 401 and 403 | 8 |

### Course AS: Async Python
| ID | Module | Status | Outcomes | Est. h |
|---|---|---|---|---|
| AS.M01 | Event loop and coroutines vs goroutines | LEARN | explain what `await` does and why blocking calls stall the loop | 5 |
| AS.M02 | asyncio: tasks, gather, timeouts, cancellation | LEARN | run concurrent I/O with timeouts and handle cancellation correctly | 6 |
| AS.M03 | Async FastAPI and async DB | LEARN | choose `async def` vs `def` endpoints correctly; use an async DB session | 6 |

### Course ARCH: Architecture and design (goal 2)
| ID | Module | Status | Outcomes | Est. h |
|---|---|---|---|---|
| ARCH.M01 | Layering and boundaries | APPLY | separate API, service and repository layers; decide where transactions live and justify it | 5 |
| ARCH.M02 | Caching with Redis | APPLY | implement cache-aside with invalidation; reason about stale reads | 6 |
| ARCH.M03 | Background work and queues | APPLY | move slow side effects to a worker; handle retries and idempotency | 6 |
| ARCH.M04 | Designing from scratch | APPLY | write a design doc (requirements, data model, API, trade-offs) and defend it in review | 8 |

### Course OPS: Production basics
| ID | Module | Status | Outcomes | Est. h |
|---|---|---|---|---|
| OPS.M01 | Docker authoring | provisional LEARN (placement check) | write a Dockerfile and a compose file for app, DB and Redis | 6 |
| OPS.M02 | Config, logging, error reporting | LEARN | 12-factor config, structured logs, no secrets in code | 4 |
| OPS.M03 | CI | LEARN | pipeline runs Ruff and pytest on every push | 4 |

## Projects
Every project uses the spec §13 headings. The learner designs and implements it; the mentor reviews and challenges.
Nothing is implemented for the learner.

### PRJ-01: Chat Export Analyzer (CLI). After PY.M04. Fully specified.
The full specification is in [content/projects/PRJ-01.md](../content/projects/PRJ-01.md). That file is the single source.

### Later projects
Full draft specifications, to be confirmed with the learner before each project starts:
[PRJ-02](../content/projects/PRJ-02.md), [PRJ-03](../content/projects/PRJ-03.md),
[PRJ-04](../content/projects/PRJ-04.md) and [PRJ-05](../content/projects/PRJ-05.md). PRJ-04 and PRJ-05 need Docker
(not installed; the learner's decision). Outline:
| ID | After | Problem | Key requirements, testing and security |
|---|---|---|---|
| PRJ-02 | DB.M04 | Message store library on SQLite | Schema design, repository layer, transactional delete-user (revisits the Q-round), placeholders only, rollback tests |
| PRJ-03 | WEB.M06 | Mini messenger REST API (FastAPI + SQLAlchemy) | Users, chats, messages, pagination, auth, 401/403/404/409 tests, migrations |
| PRJ-04 | AS, ARCH.M03, OPS | Production-style messenger | Async endpoints, Redis cache with invalidation, background notification worker, Docker Compose, CI |
| PRJ-05 | ARCH.M04, DB.M08 | Capstone: the learner designs a system from scratch | Design doc first, defended in review; Postgres; complete tests and security review |

## Written content (2026-11-12)
All modules are written. Lesson lists for every course are in `content/curriculum.json` (authoritative) and in the
site's course and module pages. Each module also has a module assessment (`content/assessments/`).

| Course | Modules | Lessons | Exercises | Auto-graded quizzes |
|---|---|---|---|---|
| PY | 7 | 28 | 27 | 177 |
| DB | 8 | 28 | 26 | 151 |
| WEB | 6 | 21 | 22 | 123 |
| AS | 3 | 10 | 10 | 47 |
| ARCH | 4 | 13 | 13 | 54 |
| OPS | 3 | 9 | 9 | 53 |
| **Total** | **31** | **109** | **107** | **605** |

PY.M01 was written and checked first. The rest was written in one pass at the learner's request (per-module review
gates waived) under `docs/CONTENT_AUTHORING.md`. It hasn't been taken by the learner yet, so expect fixes from real use.

## Recommended sequence
1. PY.M01 → PY.M04 → **PRJ-01**
2. PY.M05, DB.M01 → DB.M04 → **PRJ-02**
3. PY.M06, PY.M07 → WEB.M01 → WEB.M04 → DB.M07 → WEB.M05, WEB.M06 → **PRJ-03**
4. AS.M01 → AS.M03, ARCH.M01 → ARCH.M03, DB.M05, DB.M06, OPS.M01 → OPS.M03 → **PRJ-04**
5. DB.M08, ARCH.M04 → **PRJ-05**

## Effort (estimates, not promises)
| Block | Hours |
|---|---|
| PY | 43 |
| DB | 50 |
| WEB | 39 |
| AS | 17 |
| ARCH | 25 |
| OPS | 14 |
| Projects (10 + 12 + 25 + 25 + 30) | 102 |
| **Total** | **about 290 h** |

At 5–10 h/week that is roughly **29–58 weeks**. Placement checks can shorten this; re-learning can lengthen it.
**The first milestone (PRJ-01) is about 33 h, roughly 4–7 weeks.**

## Content sourcing
Each lesson records its sources when it is written (Phase 7): title, URL, version and verification date. Sources are official docs
first (Python, pytest, SQLite/PostgreSQL, FastAPI, Pydantic, SQLAlchemy, Docker). No sources are cited yet because no lessons
exist yet.
