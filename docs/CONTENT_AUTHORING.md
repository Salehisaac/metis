# Content authoring guide

How to write a module for this academy. **PY.M01 is the reference implementation:** read `content/lessons/PY.M01.L0*.md`,
`content/exercises/PY.M01.L0*.E1/` and `content/assessments/PY.M01.A.md` before writing anything.

## The learner (read `docs/LEARNER_PROFILE.md`)
- About 2 years of Go backend work (go-zero, MySQL, Redis, gRPC, Kafka), mostly with AI writing the code. Python is at
  syntax level. Unaided implementation is weak: they misread specs, skip edge cases, and test only the given example.
- Known Python gaps from the assessment:
  - aliasing and mutation vs rebinding
  - slice bounds clamping (missed twice)
  - `split()` vs `split(" ")`
  - custom sorting with tie-breaks (I1)
  - exceptions
  - `await` (thinks it starts a thread)
- Prefers deep "why" explanations in **short chunks, each followed immediately by practice**, with **Go comparisons**.
  Skips long written tasks, so keep tasks small and concrete.
- Rule: the learner writes all exercise code without AI. Never show an exercise's solution in its lesson.

## Files for a module `XX.Mnn` (write only these)
- `content/lessons/XX.Mnn.Lnn.md`: one per lesson listed in `content/curriculum.json`. Use the exact title from there.
- `content/exercises/XX.Mnn.Lnn.En/`: `exercise.json`, `starter/` (code plus `test_*.py`), `solution/` (solution files
  plus `SOLUTION.md`).
- `content/assessments/XX.Mnn.A.md`: the module assessment (5–6 quiz blocks, no exercise blocks).
- `content/_pending/XX.Mnn.json`: the flags for `curriculum.json`, which the orchestrator merges. **Never edit
  `curriculum.json`, `tools/`, `site/`, `tests/` or other modules' files.**

```json
{ "lessons": { "PY.M02.L01": { "exercises": ["PY.M02.L01.E1"], "quizzes": ["q1", "q2", "q3"] } }, "assessment": true }
```
`quizzes` lists the **auto-graded** quiz ids (choice, truefalse, output) **in the order they appear in the body**.
Leave out explain quizzes.

## Lesson format
- **Front matter:** JSON between `---` lines. Fields:
  - `id`, `title` (the exact title from curriculum.json), `difficulty` (beginner, intermediate or advanced), `minutes`
  - `prerequisites` (existing curriculum ids)
  - `objectives` (measurable), `why`, `applications`
  - `exercises` (must equal the flags)
  - `sources`: a list of `{title, url (https), version, verified (YYYY-MM-DD), claims[]}`
- **Body:** Markdown in numbered sections. Each section is a short explanation of *why it works*, an example, and then
  a quiz or a small task straight away. Include:
  - minimal, practical and real-world examples
  - the expected output
  - common mistakes
  - alternatives and limitations, where relevant
- **Quiz block:** a fenced block with the info string `quiz`, containing a JSON object.
  - Fields: `id` (`[A-Za-z0-9_-]`), `type`, `prompt`, `explanation`, and optionally `label` (e.g. "Debugging",
    "Application").
  - `choice`: `options` (2 or more) and `answer` (an index).
  - `truefalse`: `answer` (a boolean).
  - `output`: optional `code`, `answer`, and optional `accept` (a list of alternative answers). Spacing inside a line
    matters; leading/trailing spaces and trailing blank lines don't.
  - `explain`: `model` (shown only after the learner writes an answer).
  - `` `backticks` `` in prompts, options and explanations render as inline code. Everything else is plain text.
- **Exercise block:** a fenced block with the info string `exercise`, containing only the exercise id. Put it after
  the teaching it depends on.
- **Evidence rule:** a lesson needs at least 1 exercise, or at least 3 auto-graded quizzes, to be able to reach COMPETENT.
  Aim for **at least 3 auto-graded quizzes per lesson, plus an exercise in most lessons**.

## Exercises (checked by `tools/check_exercises.py`)
- **`exercise.json`:**
  - `id`, `lesson`, `title`, `problem`, `requirements[]`, `contract`, `expectedBehavior`, `edgeCases[]`, `evaluation[]`
  - `tests[]`: the exact pytest test function names in the starter
  - `hints[]`: exactly 3, going conceptual, then specific, then implementation
- **Starter tests must fail cleanly:** at least 1 failure and **0 errors**.
  - Import the learner's module *inside* test functions, or give the starter stubs that `raise NotImplementedError`,
    so an import problem never becomes a collection error.
  - Don't use fixtures that can fail during setup.
- **Solution files** (everything in `solution/` except `SOLUTION.md`) are overlaid on the starter, and every test must
  then pass.
  - `SOLUTION.md` shows the solution and explains why it works, plus alternatives.
- **No leaks:** the lesson must not contain 3 or more solution lines verbatim, as checked by the leak check. Teach the
  pattern on a *different* example, with different names and a different domain, and keep quiz bugs different from
  the exercise's bugs.
- **Test the edge cases** the learner tends to skip: empty input, whitespace, ties, limits and errors.
- **Exercise types:** write a function, refactor, debug (fix code so given tests pass), complete missing code.
- **Tools:** stdlib plus pytest only, unless the module is about a tool.

## Verification (do all of it, and report the evidence)
1. **Sources:**
   - Fetch every source URL with WebFetch and confirm it supports the `claims` you list.
   - Prefer official docs: `https://docs.python.org/3.12/...` (installed Python 3.12.3) and
     `https://docs.pytest.org/en/stable/...` (installed pytest 9.2.0).
   - Never cite an unfetched URL or an invented version.
2. **Examples:** run every code example with `python3` (3.12.3) in your scratch directory. Shown outputs must be the
   real outputs; you may shorten paths or trim unrelated lines.
3. **Quiz answers:**
   - Prefer runnable Python in `code`, so `tools/check_quizzes.py` executes it and compares the result.
   - For output quizzes without runnable code (shell commands, multi-file scenarios), run the scenario yourself and
     list it in your report.
4. **Module check:** run `.venv/bin/python tools/check_module.py XX.Mnn content/_pending/XX.Mnn.json` until it reports
   0 problems. It covers the validator, the exercise checker, the leak check and quiz execution.
5. **Don't** run the browser tests: memory is tight, and the orchestrator runs them once at the end.

## Modules whose lessons aren't defined yet (DB, WEB, AS, ARCH, OPS)
- **Define the lessons yourself.** Add `"newLessons": [{"id": "DB.M01.L01", "title": "..."}]` to the pending file.
  - Use 3 to 5 lessons, sized to the module's `hours` in curriculum.json at roughly 1.5–2 h per lesson including practice.
  - Make the lessons cover the module's `outcomes`.
  - IDs follow the scheme `XX.Mnn.Lnn`. The title in the lesson file must equal the title you define.
- **Respect the dependency order** in curriculum.json (`prereqs`, `sequence`).
  - You may assume what earlier modules teach. Read their lesson files if they exist, otherwise their curriculum entry.
  - Don't re-teach it at length; a short recap with a link is enough.
- **Project specs** (`content/projects/PRJ-nn.md`) use the 9 headings of `content/projects/PRJ-01.md`. Mark them with
  `content/_pending/PROJECTS.json` = `{"projects": {"PRJ-02": true}}` and check with
  `tools/check_module.py PROJECTS content/_pending/PROJECTS.json`.

## Installed tooling (project venv, pinned in requirements.txt; don't install more without the orchestrator)
pytest 9.2.0, fastapi 0.162.0 (starlette 1.10.0), pydantic 2.14.2, httpx 0.28.1, uvicorn 0.54.0, sqlalchemy 2.1.6,
alembic 1.20.1, aiosqlite 0.22.1, greenlet 3.5.6 (needed by async SQLAlchemy), pyjwt 2.15.1, python-multipart 0.0.32
(needed by `OAuth2PasswordRequestForm`), redis 8.1.0 (client library), fakeredis 2.40.0, pyyaml 6.0.3, and ruff 0.17.3.
- `fastapi.testclient.TestClient` works. It emits a `StarletteDeprecationWarning` about httpx, which is harmless.
  Don't use `-W error` in exercises.
- Async tests: use AnyIO's pytest plugin (`@pytest.mark.anyio`, installed with FastAPI). Don't add pytest-asyncio.
- Databases: use SQLite (stdlib `sqlite3`, or SQLAlchemy with `sqlite://` / `sqlite+aiosqlite://`).
  `sqlite3` is the Python module; the `sqlite3` CLI isn't installed.

## Not available on this machine: Docker, PostgreSQL, MySQL, a Redis server
- **Never show output you didn't run.** For Docker, PostgreSQL-only SQL and real Redis, either:
  - teach with a runnable local equivalent (SQLite, fakeredis, TestClient) and say plainly what differs, or
  - show the code or config and label it **"Not run on this machine (Docker / PostgreSQL unavailable); behaviour per
    the cited docs"**, with no fabricated output.
- **Exercises must pass here.**
  - Test configs statically: parse a Dockerfile or YAML and assert on its rules.
  - Use fakeredis instead of a Redis server, and SQLite instead of PostgreSQL, where the concept transfers.
- Every such limitation goes in your final report.
