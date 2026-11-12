# Platform Architecture: Proposal

**Status: APPROVED at Gate 2 (2026-11-12).** No platform code exists yet. Spec reference: §7, §9–§11, §14.

## Verified local environment (2026-11-12)
| Tool | Status |
|---|---|
| Python | 3.12.3 (`python3 -m venv` with pip works) |
| SQLite | 3.45.1, through Python's `sqlite3` module (the `sqlite3` CLI is not installed) |
| Node | 20.20.2, npm 10.8.2 (used only for dev-time JS tests, not needed at runtime) |
| Git | 2.43.0 |
| Docker, PostgreSQL, MySQL | **Not installed.** Needed only from OPS.M01/DB.M08; will ask before installing. |

## Shape
A **static site** (HTML, CSS, vanilla JS) served locally with `python3 -m http.server`. It needs a server because `fetch` of JSON or
Markdown does not work from `file://`. This uses the standard library only: no backend and no framework.
**Real Python work happens in a local workspace with pytest**, not in the browser.

```
metis/
  CLAUDE.md  plan.md  MASTER_PROMPT.md
  docs/            profile, curriculum, assessment history, architecture (source of truth for learner evidence)
  site/            the platform
    index.html     single shell page; hash routes  #/lesson/PY.M02.L03  (stable URL per item, no per-lesson HTML)
    assets/css/    design tokens, light/dark themes
    assets/js/     router, renderer, progress store, mentor-prompt builder (ES modules)
    vendor/        pinned third-party JS (see decisions D1, D2)
  content/
    curriculum.json            path/course/module/lesson tree with stable IDs and statuses
    lessons/PY.M02.L03.md      lesson text (Markdown) + front-matter JSON (incl. sources)
    exercises/PY.M02.L03.E1/   exercise.json (spec, 3 hints, evaluation) · starter/ (code + tests) · solution/ (+ SOLUTION.md)
    assessments/PY.M02.A.md    module assessment (same format as lessons)
    projects/PRJ-01.md         project specification (single source)
  workspace/       the learner's code: one folder per exercise/project, starter code + tests
  tools/           Python: content validator, workspace scaffolder
  tests/           platform tests (Python: pytest for tools; JS: node --test for pure modules; browser checks via Playwright)
  .claude/skills/  assessment, teaching, code-review (only when a phase actually needs them)
```

## Key flows
- **Lessons:** the router loads `curriculum.json` → the lesson's Markdown → the renderer produces HTML, sanitizes it, then
  highlights code. Untrusted text (search queries, imported data) is inserted only with `textContent` and `createElement`, never
  `innerHTML`.
- **Exercises:**
  - The exercise page shows the spec and a path such as `workspace/PY.M02.L03.E1/`, plus the command to run (`pytest`).
  - Hints unlock one at a time. The reference solution unlocks only after an attempt has been recorded.
  - The browser **does not claim to run Python**.
- **Exercise results (decision D3):** the learner runs `pytest --junitxml=result.xml` (built into pytest) and imports the file. The
  site records pass/fail per test as evidence. Self-marking is an alternative.
- **Progress:**
  - Stored in IndexedDB with a versioned schema and migrations.
  - Export and import as JSON, with validation and safe recovery from corrupt data.
  - Lesson statuses COMPLETED, COMPETENT and MASTERED are stored separately. MASTERED needs evidence plus a delayed recall.
  - Nothing sensitive is stored.
- **Spaced review:** each item's next-review date adapts to recall results (correct → longer interval, wrong → shorter).
  This is a heuristic, not a guarantee.
- **AI mentor:**
  - The page builds a **copyable prompt** for the chosen mode (explain, Socratic, hint, review, debug, practice, assessment,
    project).
  - The prompt includes profile excerpts, lesson objectives, exercise spec, the learner's pasted code and recent results.
  - No API keys. The site never claims access to Claude Code.
  - A `mentor/` module boundary (`buildPrompt(mode, context) → string`) lets a direct integration replace the copy step later.
- **Assessment evidence:** the browser holds day-to-day progress. Formal assessment results are also written to
  `docs/ASSESSMENT_HISTORY.md` (git-tracked) during mentor sessions, so evidence survives cleared browser data.

## Quality and verification
- Content validator (`tools/validate.py`, stdlib only) checks every lesson and exercise against its schema and verifies that IDs
  are unique and stable. Run it in tests.
- Exercises: every starter workspace's tests must **fail** against the starter code and **pass** against the reference solution.
  This is checked automatically.
- Browser checks via Playwright: no console errors, keyboard navigation, both themes, phone width.
- Python tooling for the learner's code: pytest + Ruff. A type checker gets added at PY.M05, with a decision at that point.

## Decisions needing approval
| ID | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Markdown rendering | (a) vendored Markdown parser + DOMPurify in the browser, no build step; (b) Python pre-render to HTML (adds a pip dependency and a build step) | **(a)**: fewer moving parts. Versions get pinned and verified when implemented. |
| D2 | Syntax highlighting | (a) highlight.js with a small language subset (Python, SQL, Go, bash, JSON); (b) Prism | **(a)** |
| D3 | Recording exercise results | (a) import pytest's JUnit XML, matched to the exercise's suite name and expected test names; (b) self-marking | **(a)**, with (b) as fallback |
| D4 | Exercise database | SQLite (stdlib) through DB.M07, then PostgreSQL in Docker at DB.M08 (MySQL is the day-job DB, but Postgres is the job-market default) | as stated |
| D5 | I1 attempt files in `docs/` | — | deleted at the learner's request (2026-11-12) |

## Implementation notes (Phase 3)
- **Serving:** run `python3 -m http.server` from the project root and open `/site/`. The app fetches `../content/*.json`.
- **Data contract:** schemas are enforced by `tools/validate.py` (stdlib), not by JSON Schema files. This avoids adding a
  `jsonschema` dependency, and the validator also checks things JSON Schema can't express: unique IDs, and every
  prerequisite appearing earlier in the sequence. `content/schemas/` is therefore not used.
- **Assessment data:** `content/learner/assessments.json` mirrors the scores in `ASSESSMENT_HISTORY.md` for the dashboard and
  skill profile. `docs/` stays the narrative record. Both must be updated together.
- **Browser test:** `tests/browser/check.mjs` uses playwright-core from a local path (`PLAYWRIGHT_CORE`) with the installed
  Chrome. It is not a declared project dependency yet; adding it as a devDependency is a pending decision.

## Phase 4 implementation
- **Vendored libraries** (`site/vendor/`, copied by `npm run vendor`, versions in `site/vendor/VERSIONS.json`, licences
  alongside): marked 18.1.2, DOMPurify 3.4.17, highlight.js 11.12.0 (python, sql, go, bash, json, plaintext).
  Chosen versions were at least two weeks old when pinned. Dev-only: playwright-core 1.64.1 (browser tests).
- **Rendering:** `marked.lexer` → quiz/exercise fences swapped for nonce placeholders → `marked.parser` → DOMPurify
  (`RETURN_DOM_FRAGMENT`) → blocks mounted with `h()` → highlight.js on registered languages only.
- **Quizzes:** choice, truefalse, output (normalised per line; in-line spacing matters; `accept` lists alternatives),
  explain (model answer only after the learner writes something).
- **Exercises:** `tools/scaffold.py` creates `workspace/<ID>/` with a `pytest.ini` naming the JUnit suite after the exercise
  and writing `result.xml`. The page imports that file and rejects reports for other suites.
  `tools/check_exercises.py` requires starter tests to fail cleanly and the reference solution to pass.

## Phase 5 implementation: progress
- **Event log** in IndexedDB (`metis` v1: `events` keyed by id, `meta`). Schema v1 is closed, in `site/assets/js/events.js`.
  - Event types: `lesson_started` (once per lesson), `lesson_completed`, `quiz_answer` (correct only, never answer text),
    `exercise_result` (counts only, never the XML), `hint_viewed`, `solution_viewed`, `review_done`, `bookmark`.
  - Unknown fields are dropped. IDs are format-checked, but retired IDs are valid history.
- **Derived state** (`progress.js`, pure, injected `now`). Statuses are kept separate:
  - **COMPLETED:** the learner pressed "Mark lesson as completed". Opening a lesson never completes it.
  - **COMPETENT:** completed, and every exercise passed *before* its solution was viewed (hints are recorded as
    context), and ≥ 80% of the lesson's auto-graded quizzes correct on the **first** attempt. There must be at least
    1 exercise or at least 3 auto-graded quizzes. Lessons below that bar need mentor evidence.
  - **MASTERED:** competent, plus a *due* review with ≥ 3 items and ≥ 80% first-try correct, at least 7 days after
    competence. A later failed review removes mastery until a later success.
  - **Spaced review:** intervals of 1, 3, 7, 14, 30 and 60 days. A failure restarts at 1 day.
    - Reviews count only when due. Early reviews and immediate retakes are practice and are refused by the review page.
    - In a review, feedback is withheld until every question is answered, and only first answers count.
  - All of these numbers are in `RULES`. They were **approved by the learner at Gate 5 (2026-11-12)**.
- **Formal scores are separate:** browser progress never changes `assessments.json` or `ASSESSMENT_HISTORY.md`. The skill
  profile shows lesson evidence next to the scores, not merged into them.
- **Import/export:**
  - JSON export (`metis-progress`, schema 1).
  - Import is all-or-nothing: size cap, strict validation, rejection of newer schemas. It runs in one transaction,
    duplicate ids are skipped, and re-importing the same file changes nothing.
- **Failure handling:**
  - Invalid stored records are quarantined: excluded, counted, downloadable, never deleted.
  - Blocked storage or data from a newer DB version puts the site in memory-only mode with a banner.
  - On `onversionchange` the connection closes.
  - Export and import re-read IndexedDB first, so a tab opened earlier doesn't miss events recorded in another tab.
    A tab also refreshes when it becomes visible.
  - Imported events dated more than a day in the future are rejected.
  - `navigator.storage.persist()` is requested after the first save. A backup reminder appears when there's no export,
    or the last export is more than 7 days old.

## Phase 6 implementation: AI mentor
- **Boundary:** `site/assets/js/mentor.js` exports a pure `buildPrompt(mode, context) → string` plus a `MODES` table.
  - Today the learner copies the prompt into Claude Code.
  - A future direct integration would send the same string through a small server that holds the API key.
    The frontend must never hold a key.
- **Modes (spec §10):** explain, Socratic, hint, code review (all 9 review dimensions), debugging, practice, assessment,
  project. Each mode has its own rules, and guarding modes forbid handing over solutions.
  - Assessment mode ends with a Markdown block for `ASSESSMENT_HISTORY.md` *and* a new `assessments.json` entry
    (undemonstrated = null, never 0), validated with `tools/validate.py`. This is how formal evidence gets updated.
- **Context:**
  - Learner profile and weak areas: `content/learner/profile.json` plus the latest `assessments.json` entry, optional.
  - Lesson objectives.
  - The exercise spec, expected tests, and the text of hints already seen. Never unseen hints or the reference solution.
  - The module and course of the lesson, and the specification text for a specified project.
  - Real progress: status, first-try quiz results, test results imported, hints seen, whether the solution was viewed.
  - Pasted code and the learner's question, fenced with a fence longer than any backtick run inside them.
- **Privacy:** nothing is sent, stored or logged by the site. Pasted code lives only in the page's form.
  The prompt goes wherever the learner pastes it.

## UI theme: "Transit" (chosen by the learner, 2026-11-12)
The learner chose Transit from four rendered mockups (IDE, Folio, Transit, Lab). The mockups were deleted afterwards at their request.
- **Courses are metro lines,** each with its own colour token (`--line-py`, `--line-db` and so on). Any element inside
  `[data-course]` picks up its line as `--line`: sidebar, lesson headers, quiz and exercise blocks, progress cards.
- **The dashboard route map** (`site/assets/js/metro.js`) is built from `curriculum.json` and real progress:
  - one line per course and one station per module, in sequence order; projects are diamonds
  - dashed transfers where the route changes line
  - "You're here" sits at the next lesson's module
  - every station is a focusable link with a descriptive label
- **Motion:** one orchestrated moment (the lines draw, then a train rides to "You're here"), plus short feedback pops in
  answer to the learner's actions. Everything is disabled under `prefers-reduced-motion`.
- **Type:** Barlow and Barlow Condensed (SIL OFL), vendored as woff2 files in `site/vendor/fonts` (`@fontsource` 5.3.0).
  Nothing is loaded from third-party servers.
- **Themes:** dark by default; the button cycles dark → light → system. Every text token meets WCAG AA (4.5:1) in both
  themes, checked by script.

## Known limitations
- Project test suites and reference solutions are served as static files, so "hidden until asked" relies on honesty.
- Time-based rules (mastery delay, review schedule) trust the computer's clock.
- A progress export can be hand-crafted, just as a JUnit XML file can be hand-edited. Browser evidence is strong but
  not proof; formal scores come from mentor sessions.
- Module assessment answers are recorded and summarised (first attempts) on the module page. They don't feed any status yet.
- Reviews reuse the lesson's own quiz questions, so they can be recalled by rote. Fresh questions come from mentor practice mode, which happens in Claude and doesn't count toward reviews or statuses.
- Progress lives per browser profile. Export/import is the only way to move or back it up.
- **Environment:** Docker, PostgreSQL, MySQL and a Redis server aren't installed. Lessons use runnable local equivalents
  (SQLite, fakeredis, TestClient, static checks of Dockerfiles, compose files and CI YAML) and label everything else
  "Not run on this machine". PRJ-04 and PRJ-05 need Docker, which is the learner's decision.
- Starlette 1.10 emits a `StarletteDeprecationWarning` about httpx in `TestClient`. It's harmless; revisit when upgrading
  FastAPI and Starlette.
- Project work (PRJ-0n) can't be imported as JUnit evidence on the site, because only exercises are wired up. The mentor
  records project results.
- None of the 109 lessons has been taken by the learner yet (as far as the project files show). All exercises pass the checker against their reference
  solutions, but difficulty and clarity still need validating through use.
- The mentor can't see the conversation it starts. Its advice and any assessment results come back only if the
  learner (or Claude, in a session) records them in `docs/`.
- Imported reports are checked per test case (suite name, every expected test present, each status), but a hand-edited
  XML file can still claim a pass. Treat it as strong-but-not-proof evidence; mentor review of the code is the backstop.
- Browser progress is per browser profile. Export it regularly; formal evidence is also kept in `docs/`.
- Docker is unavailable until installed (only needed from OPS.M01).
