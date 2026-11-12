# Project Plan

Spec: `MASTER_PROMPT.md`. Each phase ends with a gate. **GATE** = stop and wait for explicit user approval.
Every phase completion also follows the Definition of Done (spec §16): verify, test, check console/navigation/
responsiveness/persistence/failure cases, update docs, report known limitations.

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done

---

## [x] Phase 0 — Interview (no code)
Goal: understand the learner before assessing.

Milestones
- [x] Background: Python, other languages, real applications built
- [x] Domains: FastAPI, OOP, SQL/databases, HTTP/REST, Git, Docker, architecture, AI tools/agents
- [x] Existing projects/repos identified; permission asked for read-only inspection
- [x] (If permitted) read-only review of existing projects: structure, deps, tests, quality
- [x] Goals listed and prioritized with the user
- [x] Learning style and weekly study time

Acceptance criteria
- Questions asked one at a time, adapted to answers, no repeats.
- `docs/INTERVIEW_NOTES.md` records answers as **self-reported** (not evidence of skill).
- Short summary of initial understanding + estimated starting points per domain.

**GATE 0:** user confirms the summary is accurate → start assessment.  ✅ approved 2026-11-12

---

## [x] Phase 1 — Adaptive assessment (no platform code)
Goal: measure what the learner can actually do.

Milestones
- [x] Assessment plan: which domains, starting difficulty, formats (based on Phase 0)
- [x] Per topic: challenge → independent answer → evaluate → explain mistakes → find gap → adjust
- [x] Practical formats used: predict output, code writing, small design (as options). Written SQL was skipped by the learner.
      Refactoring and debugging of unfamiliar code are **deferred to placement checks and lessons** (see ASSESSMENT_HISTORY.md).
- [x] Project review (done read-only in Phase 0; see INTERVIEW_NOTES.md)

Acceptance criteria
- Every assessed competency scored 0–4 on A/B/C/D separately, each with evidence and confidence.
- Unassessed competencies marked "Not assessed" (never 0, never assumed competent).
- No answers revealed before the learner attempts.
- Results appended to `docs/ASSESSMENT_HISTORY.md` with date.

**GATE 1:** user reviews assessment results. ✅ approved 2026-11-12

---

## [x] Phase 2 — Learner profile, curriculum, architecture proposal
Deliverables
- `docs/LEARNER_PROFILE.md` (all spec §5 sections, evidence-backed)
- `docs/CURRICULUM.md`: every topic tagged SKIP/REVIEW/LEARN/DEEPEN/APPLY with reason;
  Path → Course → Module → Lesson → Exercise → Assessment → Project; stable IDs;
  measurable outcomes per module; dependency map; sequence; projects; effort estimates (labelled as estimates)
- `docs/ARCHITECTURE.md`: platform proposal (default stack per spec §7.1; any deviation with trade-offs)

Acceptance criteria
- No topic included/excluded without a stated reason tied to evidence or goals.
- Prerequisites satisfied before advanced topics in the sequence.
- User can reprioritize; changes reflected in files.

**GATE 2:** user approves curriculum **and** architecture. Nothing in Phases 3+ starts before this. ✅ approved 2026-11-12 (D1a, D2a, D3a, D4)

---

## [x] Phase 3 — Platform foundation
Dashboard shell, sidebar/breadcrumb/prev-next navigation, design system (dark/light), reusable templates,
stable lesson routes, no per-lesson duplicated HTML.

Acceptance: keyboard navigable, responsive, WCAG 2.2 AA practices, no console errors, dashboard shows
only real stored data (empty states otherwise).

Verified 2026-11-12:
- validator OK; pytest 9 passed; node --test 7 passed.
- Browser check (`tests/browser/check.mjs`, headless Chrome): 17 routes render with no console errors. Focus moves to h1
  on navigation. The skip link works. An XSS probe via search inserted no markup. Theme cycles light, dark, system.
  At 375px wide there is no horizontal overflow, the menu has aria-expanded, and Escape closes it.
- Contrast: text tokens are at least 5.68:1 in both themes; the focus ring is at least 4.72:1.
- Failure cases: a curriculum fetch that returns HTTP 500 or invalid JSON shows the error view, with no uncaught errors.
- WCAG 2.4.11 (focus not obscured): after Shift+Tab, focus stays below the sticky bar at 1280px and 375px. A negative control
  with the padding removed fails as expected.
- Not done: screen-reader testing, a full WCAG audit.

Deferred, as planned: bookmarks and progress indicators (Phase 5 store); lesson and project rendering (Phase 4).

**GATE 3:** user reviews foundation. ✅ approved 2026-11-12

## [x] Phase 4 — Learning engine
Lesson renderer (spec §8 structure), quizzes, exercises with progressive hints (solution locked until attempt),
assessments, local exercise workspaces with venv/pytest instructions.

Acceptance: content validated by the `tools/validate.py` contract (chosen instead of JSON Schema files; see ARCHITECTURE.md);
safe DOM APIs for untrusted text; tests pass.

Verified 2026-11-12 (all against `tests/fixtures/content`; no real lessons exist yet):
- pytest: 30 passed. These cover the content contracts (both directions between files and flags, sources, quizzes,
  3 hints, separate solution), the scaffolder (never copies the solution, refuses to overwrite, rejects bad IDs) and the
  exercise checker (catches a starter that is already solved, import errors, a broken solution).
- `npm run test:js`: 11 passed (front matter parsed the same way as in Python, output normalisation, grading, JUnit verdict).
- `npm run test:browser`: Phase 3 checks plus 35 engine checks, 0 problems, 0 console warnings:
  - Hostile Markdown is neutralised (script, img onerror, iframe, javascript: link).
  - Quiz and exercise HTML is shown as text. A malformed block shows an inline error.
  - All 4 quiz types work; multiple choice works by keyboard alone.
  - Hints unlock in order. The solution is fetched only after a confirmed request.
  - Real pytest JUnit reports are accepted. Reports for the wrong suite, reports with an expected test removed,
    garbage XML and XXE are rejected safely.
  - Focus moves to each newly revealed hint.
  - Failure paths (lesson 500, bad front matter, invalid exercise.json, solution 500) show error boxes with no uncaught errors.
  - Assessment, exercise and project routes work. A full lesson has no horizontal overflow at 375px.
- Session-only: quiz answers and imported results are not stored (Phase 5).

**GATE 4** ✅ approved 2026-11-12. Sequencing decision: follow the planned phase order (Phases 5–6 before content).

## [x] Phase 5 — Progress system
IndexedDB with versioned schema, COMPLETED/COMPETENT/MASTERED tracking with evidence, spaced review,
export/import with validation, recovery from corrupt data.

Acceptance: persistence verified across reloads; invalid import rejected safely; no secrets stored.

Verified 2026-11-12 (fixture content):
- `npm run test:js`: 26 passed. The pure model covers:
  - opening ≠ completing
  - first attempt only
  - a pass after viewing the solution doesn't count
  - minimum evidence
  - no mastery at day 3, mastery at day 7+
  - reviews that aren't due (early or an immediate retake) are practice only
  - a later failure removes mastery and resets the interval
  - out-of-order and retired events
  - closed event schema, all-or-nothing import, and events dated in the future rejected
- pytest: 31 passed. The validator enforces that `quizzes` in curriculum.json equal the lesson's auto-graded quiz ids,
  and checks the quiz id format.
- `tests/browser/progress.mjs`: 27 checks, stable over repeated runs.
  - Statuses: started → competent; persistence across reload; bookmarks.
  - Dashboard counts and history.
  - Clock-driven review → mastery, with first-answer-only reviews.
  - Reviews that aren't due are refused. Review feedback is withheld until the end.
  - An export from a stale second tab includes events recorded in another tab.
  - Export holds no answer text. Export → fresh-browser import reproduces the status, and re-import adds nothing.
  - 4 kinds of invalid import are rejected with no change.
  - A corrupt record is quarantined and the site still works.
  - With blocked storage there's a banner and memory-only mode. Newer-version data is left untouched, with a banner.
- No secrets are stored: the closed schema has no free-text fields.

**GATE 5** ✅ approved 2026-11-12. Teaching rules (RULES) approved as proposed: 80% first-try; ≥1 exercise or ≥3 quizzes; due reviews only; mastery ≥7 days after competence; intervals 1/3/7/14/30/60.

## [x] Phase 6 — AI mentor
Copyable prompt workflow for the 8 modes (explain, Socratic, hint, review, debug, practice, assessment, project),
including profile/lesson/objectives/code/results. Clean boundary for future direct integration; no API keys in frontend.

Verified 2026-11-12:
- `npm run test:js`: 37 passed. The mentor tests cover:
  - all 8 modes, with every context section
  - the context each mode requires
  - guarding modes forbid solutions; review lists all 9 dimensions
  - the reference solution never appears in a prompt
  - fence breakout prevented
  - hint mode shows only the hints already seen
  - assessment mode outputs both `ASSESSMENT_HISTORY.md` and `assessments.json`, using null rather than 0
  - observations are labelled as the mentor's
  - project mode includes the spec
- pytest: 32 passed (profile.json contract added).
- `tests/browser/mentor.mjs`: 15 checks.
  - The lesson and exercise links preselect the right mode and context.
  - The prompt contains objectives, profile, weak areas and real progress (hints seen 2 of 3).
  - Copy puts the exact prompt on the clipboard. Missing context gives a clear message.
  - Pasted code is fenced safely. No solution or unseen hint text appears.
  - **No request leaves the machine.** There's no overflow at 375px.

**GATE 6** ✅ approved 2026-11-12. profile.json confirmed accurate by the learner.

## [x] Phase 7 — Educational content
Populate personalized courses one module at a time. Each module: sourced (title, URL, version, verified date),
code examples run, exercises have tests, answers validated.

**GATE per module:** user reviews module before the next is produced.
**Decision 2026-11-12 (learner):** "power through all and write them". The per-module review gate is waived. The
remaining modules are written in one go, under the same verification standard (`docs/CONTENT_AUTHORING.md`), and
reviewed together afterwards. A second request the same day, "complete the whole project", extends this to every
remaining course and project, followed by Phase 8.
- Learner dependencies are pinned in `requirements.txt` (releases at least 14 days old): FastAPI, Pydantic, SQLAlchemy,
  Alembic, httpx, uvicorn, aiosqlite, PyJWT, redis, fakeredis, PyYAML. Ruff 0.17.3 is installed by PY.M06.
- Docker, PostgreSQL, MySQL and a Redis server are not installed. Content uses runnable local equivalents (SQLite,
  fakeredis, TestClient, static config checks) and labels anything not run here. Installing Docker is the learner's
  decision (needed for PRJ-04/05).

### PY.M01: written 2026-11-12, awaiting review
Content:
- 4 lessons (L01–L04), with 23 quizzes in total, 20 of them auto-graded (each lesson has 5, so 4 of 5 meets the 80% rule).
- 3 exercises:
  - L01.E1: refactor to `main()` plus the `__main__` guard
  - L03.E1: fix bugs using only pytest's output
  - L04.E1: write a `.gitignore`, checked with real Git
- The module assessment PY.M01.A (6 questions). The Git placement check is in L04.

Verification:
- Sources fetched 2026-11-12: Python 3.12 docs, the pip user guide, the PyPA externally-managed specification,
  pytest docs, Git docs and Pro Git. The pip 24.0-specific docs URL returned 404, so the stable docs (v26.3) are cited and
  the pip behaviour was verified locally on 24.0.
- Every example was run locally (Python 3.12.3, pip 24.0, pytest 9.2.0, git 2.43.0), and outputs are copied from those runs.
- `tools/check_quizzes.py` executes Python output quizzes. Shell-command quizzes were checked by running the commands:
  `-c` argv, `len(argv)`, `__name__`, `sys.prefix`, `rev-parse`.
- `tools/check_exercises.py`: all 3 exercises pass. Starters fail cleanly, solutions pass, and test names match `exercise.json`.
- `tests/browser/content.mjs`: every real lesson, exercise, assessment and project renders, with no console warnings.
  Every auto-graded answer key is accepted by the site.
- Learner/editor edits made 2026-11-12 18:39 were kept: L01's shout.py example (verified by running it), L02's go.mod/go.sum
  wording, and L04's placement-check follow-up.
- Totals: pytest 35, JS 37, browser 90 checks.
- Environment note: headless Chrome crashed twice ("Target crashed") while the host had about 2 GB of free RAM. Reruns passed.
  This isn't an app failure, but browser suites can flake when the machine is low on memory.

### PY.M01: Setup and the feedback loop (written 2026-11-12; review gates later waived by the learner)
Content:
- 4 lessons (L01 running Python, L02 venv/pip, L03 pytest, L04 workspace, Git and the Git placement check)
- 3 exercises: L01.E1 refactor to an importable/runnable script; L03.E1 fix code from test failures; L04.E1 .gitignore
- module assessment PY.M01.A (6 questions)

Verification:
- **Sources:** 10 official pages fetched and checked against the claims they support: Python 3.12 docs, pip, the PyPA spec,
  pytest, Git docs and Pro Git. The pip 24.0 docs URL returns 404, so the stable docs (v26.3) are cited and the
  behaviour was verified locally with pip 24.0.
- **Examples:** every code example and output was run locally on Python 3.12.3, pip 24.0, pytest 9.2.0 and git 2.43.0.
  Shown outputs are real outputs, sometimes shortened or trimmed (paths, unrelated lines).
- **Exercises:** `tools/check_exercises.py` passes all 3 (starter tests fail cleanly, reference solutions pass,
  test names match exercise.json).
  - **No solution leaks:** a new leak check finds no lesson printing 3 or more of its exercise's solution lines.
    The only match is the `__main__` guard idiom that L01 teaches.
  - The first draft did leak: L01's example was the E1 solution, and L03 q5 used E1's bug. Both were rewritten.
- **Quiz answers:** `tools/check_quizzes.py` executes the Python output quizzes (2, both correct). The 5 shell-command
  output answers were verified by running the commands (argv with -c, __name__ on import, sys.prefix in a venv,
  git rev-parse after switch -c, argv length).
- **Validator:** OK (flags, sources, quiz id lists, 3 hints, separate solutions).
- **Tests:** pytest 36, JS 37, browser 90 checks. A new real-content sweep renders every lesson, exercise, assessment
  and project with no errors and inline code in quiz text.
- **Not verified:** an end-to-end run by the learner. That is the module review.

### All courses: written 2026-11-12 (14 parallel authoring agents, merged and checked by the orchestrator)
| Course | Modules | Lessons | Exercises | Auto-graded quizzes |
|---|---|---|---|---|
| PY | 7 | 28 | 27 | 177 |
| DB | 8 | 28 | 26 | 151 |
| WEB | 6 | 21 | 22 | 123 |
| AS | 3 | 10 | 10 | 47 |
| ARCH | 4 | 13 | 13 | 54 |
| OPS | 3 | 9 | 9 | 53 |
| **Total** | **31** | **109** | **107** | **605** |

Every module has a module assessment. PRJ-02 to PRJ-05 have draft specifications, to be confirmed with the learner.

Process:
- Each module passed `tools/check_module.py` (validator, exercise checker, leak check, quiz execution) before its flags
  were merged with `tools/merge_pending.py`. Merges ran only on exit code 0.
  - Exception: PY.M03 was merged after its checker crashed on another module's half-written file. It was re-verified
    after the merge and is clean; the checker now skips malformed files outside the module being checked.
- Dependencies added during authoring, each pinned and released at least 14 days earlier:
  - `greenlet==3.5.6`, required by async SQLAlchemy
  - `python-multipart==0.0.32`, required by FastAPI's OAuth2 form login
  - `ruff==0.17.3`

  The affected lessons (AS.M03.L03 and WEB.M06.L03) were then rerun with real output.
- Orchestrator review fixes:
  - WEB.M03.L02 and WEB.M02.L03 were restructured, because their examples gave away the exercise code shape.
  - A stale "FastAPI isn't installed" sentence in PY.M07.L04 was corrected; its `Depends(get_db)` claim was verified
    on FastAPI 0.162.0.
- Incidents, all resolved:
  - An agent's mistyped glob briefly wrote files into another agent's exercise folders. They were removed, and the
    owner verified its folders were complete.
  - An agent created a stray venv at `/opt-demo`, outside the project (16 MB). It was left for the learner to remove.

### UI redesign: "Transit" (2026-11-12, learner request: "the UI is a bit boring")
- Four directions were mocked up with live animation and screenshots; the learner picked **C, Transit**. The mockups were
  deleted at the learner's request.
- Implemented across the real site:
  - a route map generated from real data
  - course-line colours throughout, and the roundel logo and favicon
  - vendored Barlow fonts
  - dark default plus a light theme
- Verified: JS 40 (including map layout tests), the browser suites (see Phase 8), and contrast at or above 4.5:1 for
  every text token in both themes.

## [x] Phase 8 — Final verification
Functionality, accessibility, security, content accuracy. Report known limitations.

Results:
- **Content:**
  - `tools/validate.py` is OK: 31 modules, 109 lessons, 107 exercises, 605 auto-graded quizzes, 5 projects, and every
    flag, source, quiz list and hint count is consistent.
  - `tools/check_exercises.py`: all 107 exercises pass. Starters fail cleanly, solutions pass, test names match, and no
    solution leaks into its lesson.
  - `tools/check_quizzes.py`: 332 output answers executed, all correct. The remaining shell-command answers were
    verified by their authors running them.
- **Unit tests:** pytest 36 and JS 40 pass. The JS count includes the route-map layout tests.
- **Browser** (headless Chrome, real content, Transit theme): all suites pass, 578+ checks.
  - Route sweep and keyboard: skip link, focus never hidden under the top bar, every route-map station reachable and
    labelled.
  - XSS probes (Markdown, search, imports, JUnit XXE) are neutralised.
  - Failure paths show error boxes, with no uncaught errors.
  - Progress: persistence, mastery rules, export and import, quarantine, blocked storage, stale tabs.
  - The mentor sends nothing off the machine, and solutions are never in prompts.
  - Every lesson, exercise, assessment and project page renders with no console warnings.
- **Accessibility:** contrast is at least 4.5:1 for every text token in both themes. Reduced motion is respected and
  the layout works at 375px. No screen-reader test or full WCAG audit was done.
- **Security:**
  - Content goes through one sanitised HTML path (DOMPurify); all other text is set with textContent.
  - No secrets are stored, the event schema is closed, and imports are validated.
  - Nothing is loaded from third parties at runtime: fonts and libraries are vendored.
- **Known limitations:** see `docs/ARCHITECTURE.md`. The main ones:
  - Docker, Postgres and Redis aren't installed here.
  - The lessons haven't been taken by the learner yet.
  - Evidence from reports and exports can be hand-edited.
  - Time-based rules trust the computer's clock.

**GATE 8** ✅ signed off by the learner, 2026-11-12. Decisions taken at sign-off:
- Docker: install later; decide on reaching PRJ-04.
- `/opt-demo` (stray venv) and the `design/` mockups: the learner asked for both to be deleted. The safety check blocked
  the deletion, so the learner runs `rm -rf /opt-demo /root/go/metis/design` themselves.
- Defaults accepted:
  - no PostgreSQL driver until DB.M08 or PRJ-05
  - `scrypt` for password hashing
  - OPS teaches both CI platforms
  - project code in `workspace/PRJ-nn/`
  - no `git init`
  - the WEB teaching choices
- Next: the learner starts at PY.M01.L01. Lesson fixes come from real use.

**GATE 8:** user signs off.
