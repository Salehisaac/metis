# Metis — Personalized Python Backend Academy

Full spec: `MASTER_PROMPT.md` (source of truth). Phases, gates and acceptance criteria: `plan.md`.

## Current phase
All phases complete; Gate 8 signed off 2026-11-12. Docker: install later (decide at PRJ-04). All 31 modules, 109 lessons and 5 projects are written; the UI is the "Transit" theme.
New or changed content follows docs/CONTENT_AUTHORING.md and must pass tools/check_module.py before merging. Update this line when a gate is passed.
Agreed rule: learner uses no AI on exercises/assessments; AI is mentor only, after an attempt.

## Hard rules
- Never assume the learner's level; every claim about their skill needs recorded evidence.
- Never proceed past an approval gate (see `plan.md`) without explicit user approval.
- Phases 0–2: no application code, no HTML, no lessons, no curriculum before assessment is done.
- Never reveal exercise solutions before an attempt. Never equate quiz score or "opened" with mastery.
- Never claim code/tests work without running them. Never invent docs, links, or version numbers.
- Never modify the user's existing projects; inspect read-only and only with permission.
- No significant dependency or architecture change without explaining why and getting approval.
- No secrets in frontend code or browser storage. Treat stored/imported data as untrusted.

## Assessment
- Score each competency 0–4 on four separate dimensions: A conceptual, B implementation,
  C debugging, D real-world application. Record evidence + confidence (High/Medium/Low/Not assessed).
- Not assessed ≠ 0. Never average dimensions into a mastery label.
- Prefer practical formats (predict output, debug, write, refactor) over multiple choice.
- Lesson statuses are separate: COMPLETED / COMPETENT / MASTERED.
- Curriculum statuses: SKIP / REVIEW / LEARN / DEEPEN / APPLY.

## Persistence
Files are the source of truth for learner data (not chat memory):
`docs/INTERVIEW_NOTES.md` (Phase 0), `docs/ASSESSMENT_HISTORY.md`, `docs/LEARNER_PROFILE.md`,
`docs/CURRICULUM.md`. Append; keep history so progress can be compared.
Structured copies: `content/curriculum.json`, `content/learner/assessments.json` and `content/learner/profile.json` are authoritative for structure/scores/profile
(the site reads them); `docs/*.md` is the narrative. Update both together, then run the validator.

## Default stack (after approval only)
Static HTML/CSS/vanilla JS, Markdown + JSON content, IndexedDB with versioned schemas,
local Python + pytest + real FastAPI apps. No React/Vue/DB server/backend without justified approval.

## Commands
- Setup: `python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt` · `npm install && npm run vendor`
- Serve: `python3 -m http.server 8765 --bind 127.0.0.1` (repo root) → http://127.0.0.1:8765/site/
- Validate content: `.venv/bin/python tools/validate.py` · exercises: `.venv/bin/python tools/check_exercises.py` · quiz answers: `tools/check_quizzes.py`
- One module before merge: `tools/check_module.py MODULE content/_pending/MODULE.json` · merge flags: `tools/merge_pending.py` · output-quiz answers: `.venv/bin/python tools/check_quizzes.py`
- Tests: `.venv/bin/pytest -q` · `npm run -s test:js` · `npm run -s test:browser` (needs the server running)
- Learner workspace: `.venv/bin/python tools/scaffold.py <EXERCISE_ID>` (refuses to overwrite)

## Content rules
- Authored files ⇔ flags in curriculum.json (`authored`, `exercises`, `assessment`, `specified`); validator enforces both ways.
- Every lesson: §8.1 front matter + `sources` (title, https URL, version, verified date, claims). Exercises: exactly 3 hints,
  reference solution in `solution/` (never copied to workspace). Starter tests must fail cleanly; solution must pass.
- Engine test content lives only in `tests/fixtures/content/`, never in `content/`.
- Writing content: fetch every source, run every example and expected output locally, and pin claims to installed versions.
- Text goes into the DOM via `h()`/textContent. Sole HTML path: `render.js` (marked → DOMPurify RETURN_DOM_FRAGMENT).
- Authored lessons list their auto-graded quiz ids in curriculum.json `quizzes` (validator checks against the body).

## UI rules (Transit theme)
- Pages take their course colour from `[data-course]` (`--line`); colours are tokens in main.css, AA-checked in both themes.
- The dashboard route map (`metro.js`) is built only from curriculum.json plus real progress. Never show invented stats.
- One orchestrated animation (the map); everything else is feedback to the learner's actions; respect reduced motion.

## Progress rules
Statuses come only from the event log (`site/assets/js/progress.js`, thresholds in `RULES`; see ARCHITECTURE.md).
Browser progress never edits `assessments.json` / `ASSESSMENT_HISTORY.md`: formal scores change only in mentor sessions.

## Session report
End substantial sessions with: completed, files changed, tests run + results, open problems,
decisions needing approval, next action.
