# PRJ-01: Chat Export Analyzer (CLI)

Starts after PY.M04. Estimated 10 h. Approved at Gate 2 (2026-11-12).

1. **Problem:** analyze a JSON export of a chat (`id`, `sender`, `text`, `timestamp` in ISO 8601) and report statistics.
2. **Functional requirements:**
   - `top-senders --n N`: ranking with ties broken alphabetically.
   - `activity --by hour|weekday`.
   - `search WORD`: case-insensitive whole-word match.
   - `--since DATE` filter.
   - Blank or whitespace-only texts are ignored.
   - Malformed records are skipped and counted in a warning.
   - `--json` output option.
3. **Non-functional:**
   - Standard library only.
   - Deterministic output.
   - Exit codes: 0 OK, 1 input error, 2 usage error.
   - Handles 100k messages quickly. Measure it; no target is promised.
4. **Architecture:** the learner writes a short proposal *before coding*. It must separate pure analysis functions from I/O and
   the CLI. The mentor reviews it.
5. **Milestones:**
   - M1 load and validate
   - M2 `top-senders` (revisits I1)
   - M3 activity and since
   - M4 search
   - M5 CLI and JSON
   - M6 final review
6. **Testing:**
   - Tests are written before each milestone.
   - Required edge cases: empty file, all-blank texts, ties, `n` larger than the number of senders, bad timestamps, Unicode names.
   - At least 1 end-to-end CLI test.
7. **Security:**
   - The input file is untrusted: no `eval`.
   - Malformed or unexpected JSON types are handled without crashing.
8. **Rubric (100 points):**
   - Correctness on a hidden test suite: 40
   - Learner's tests: 20
   - Error handling: 15
   - Clarity: 15
   - Separation of concerns: 10
   - Pass = 70 or more **and** all core hidden tests pass.
9. **Final review:** code review in mentor review mode, plus a learner self-review. Evidence goes to `ASSESSMENT_HISTORY.md`.
