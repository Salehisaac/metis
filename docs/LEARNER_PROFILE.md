# Learner Profile

Baseline: **Assessment 1 (2026-11-12)**. Sources: `INTERVIEW_NOTES.md` and `ASSESSMENT_HISTORY.md`.
Evidence labels: **[demo]** shown in the assessment (with the challenge ID) · **[self]** self-reported ·
**[AI-shipped]** exists in the learner's repos but was written with AI help, so it is not evidence of independent skill.

## 1. Background
- About 2 years (2024-12 to 2026-11) on a team building a Telegram-compatible messenger in Go (teamgram, go-zero
  microservices, MySQL, Redis, gRPC, Kafka). Did not design the base architecture. Added features and improvements
  (about 1,385 commits). [observed git history]
- **AI wrote most of the code**: the learner describes, the AI implements, the learner reviews. [self, confirmed by `Co-Authored-By: Claude`
  trailers]
- Laravel: personal projects only. [self] Python: syntax-level tutorials only. [self] No Python or PHP in authored history.

## 2. Learning objectives
1. **Python backend job** (Python + FastAPI). Primary.
2. **Architecture and design**: designing systems themselves rather than only adding features. Develops alongside goal 1.
- Not current goals: AI engineering, interview prep.

## 3. Existing experience
- Daily exposure to a production microservice system: RPC, caching, queues, migrations. [AI-shipped]
- Git: branches, conflicts, rebase, PR/MR review, blame/bisect. [self]
- Docker: runs existing setups; doesn't write Dockerfiles. [self]
- OOP: Go-style only (structs, interfaces, composition). [self]

## 4. Demonstrated strengths
- Writes basic Go fast: maps, loops, structs, `continue`, idiomatic `counts[k]++`, all in about 5 minutes. [demo I1]
- Learns from a clear explanation within one session: aliasing was wrong in P1 and right in P2. [demo P1→P2]
- Sound backend design instincts (conceptual only, Low confidence): queue-based fan-out, PUT idempotency, cache
  invalidation, 409 Conflict, test DB or fakes. [demo Q-round]

## 5. Weaknesses
- **Going from spec to working code unaided.** Misread the requirement, didn't implement ranking, didn't check edge cases,
  and tested only the given example. [demo I1]
- Doesn't recall syntax unaided, even in Go (composite literals, parameter declarations). [demo I1]
- Python semantics: rebinding vs mutation, slicing rules (missed twice), string methods. [demo P1, P2]
- Avoids written tasks when unsure (skipped S1 and I1 attempt 2). [observed]

## 6. Knowledge gaps (in priority order)
1. Independent implementation and testing habit (spec → edge cases → tests → code).
2. Python language fundamentals and idioms.
3. Transactions and atomicity. Misconception: "the crash leaves both statements done." [demo Q-round]
4. Safe SQL: knows injection is a risk, but proposed manual escaping. [demo Q-round] Also JOINs and locking. [self: struggles]
5. Writing tests. Has never written one; the adminpanel tests are AI-written. [self]
6. Python async. Thinks `await` starts a thread. [demo Q-round]

## 7. Practical abilities
- Can write small Go programs with documentation and debugging help. Cannot yet produce correct, tested solutions unaided.
- Python: no independent code written yet (Not assessed).

## 8. Learning preferences
- Stated: **deep explanation first**; options-style questions for interviews; 5–10 h/week; no AI on exercises
  (agreed rule).
- Observed: prefers speed and skips long written tasks.
- Resolution: short, deep explanation chunks (the "why"), each followed immediately by a small task with instant feedback (tests).
  Explanations draw comparisons with Go where that helps.

## 9. Assessment results
Full table: `ASSESSMENT_HISTORY.md` → "Assessment 1 — results". Summary:
- A (conceptual) 2 for HTTP, caching, event-driven design, testing and injection awareness (Low confidence).
  A 1 for Python fundamentals and SQL basics. A 0 for transactions and Python async.
- B (independent implementation) 2 in Go with help. Python and SQL B are Not assessed.
- C (debugging) 1 in general and in testing.
- D (real-world) Not assessed anywhere, because repo work is AI-shipped.

## 10. Assessment confidence
- Medium: Python fundamentals, unaided Go implementation.
- Low: all conceptual items asked as options, and SQL basics (self-report).
- Not assessed: written SQL, written Python, debugging unfamiliar code, refactoring, Git, Docker, FastAPI/Pydantic/SQLAlchemy.
  Each gets a short placement check when its module starts.

## 11. Recommended learning priorities
1. Python fundamentals with a test-first habit from day one (pytest supplied, then written by the learner).
2. Data modeling and SQL with transactions (SQLite first).
3. HTTP and FastAPI, applying the REST concepts the learner already has.
4. Async Python, then async FastAPI.
5. Architecture: design small systems themselves, with trade-offs reviewed.

## History
| Date | Event |
|---|---|
| 2026-11-12 | Assessment 1 baseline (Phase 0 interview and Phase 1 assessment). |
