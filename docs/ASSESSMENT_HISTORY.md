# Assessment History

Scale 0–4 per dimension: A conceptual · B independent implementation · C debugging · D real-world application.
Confidence: High / Medium / Low / Not assessed. "Not assessed" ≠ 0. Rule: no AI during challenges.
Answer keys are never written here before the learner attempts a challenge.

## Assessment 1 — started 2026-11-12

### Plan
Starting level comes from Phase 0. Concepts transfer from Go; Python is self-reported at syntax level;
unaided implementation is unknown.

| Order | Domain | Formats | Starting difficulty |
|---|---|---|---|
| 1 | Python fundamentals and data structures | predict output, write small function | basic, raised quickly if strong |
| 2 | Python functions, errors, OOP (classes) | predict output, debug, write | basic |
| 3 | Unaided implementation (language of choice, then Python) | write code from a spec | small |
| 4 | SQL and data modeling | write queries, spot bugs (transactions, injection) | intermediate |
| 5 | HTTP/REST API design | design endpoints, status codes, errors | intermediate |
| 6 | Caching and consistency (Redis) | explain and debug scenarios | intermediate |
| 7 | Testing | write tests for given code | basic |
| 8 | Architecture | small design problem with trade-offs | intermediate |

Domains deferred (not relevant yet, or prerequisites missing): FastAPI, Pydantic, async Python, SQLAlchemy,
Docker authoring, CI/CD. These are **Not assessed**. FastAPI is skipped because the learner has no experience with it.

### Log
<!-- One entry per challenge: id, format, learner answer summary, result, gap identified, next step. -->

#### P1: Python fundamentals, predict output (2026-11-12)
Tested: list aliasing, slicing copy, `sort`, negative index, slice bounds, `str.split()`, `dict.get` counting idiom.
- Learner answer: `[3, 1, 2]` / `[1,2,3]` / `3 2` + "index out of range on nums[1:3]" / `{"g":2,"o":2,"p":1,"y":1}`
- Correct: `[3, 1, 2, 4]` / `[1, 2, 3, 4]` / `4 4 [1, 2]` / `{'go': 2, 'py': 1}`
- Results:
  - ✗ **Aliasing**: assumed `other = nums` copies the list, so `append` was missed on `nums`. Gap: names vs objects, in-place mutation.
  - ✓ `nums[:]` copy and `sort()` on the copy leave the original untouched. Consistent with their (wrong) aliasing model.
  - ✓ `len`, `nums[-1]`. Correct under their model.
  - ✗ **Slicing**: expected an error for `nums[1:3]` on a 3-element list. Gap: end-exclusive bounds (same as Go), and the fact
    that Python slices clamp instead of raising.
  - ✗ **`str.split()`**: treated it as splitting into characters (spaces ignored). Gap: string methods.
  - ✓ The `counts.get(k, 0) + 1` counting logic is correct.
- Next: P2 re-tests aliasing through a function parameter, rebinding vs mutation, out-of-range slice, and `split(sep)` in a new form.

#### P2: functions, mutation vs rebinding, predict output (2026-11-12)
- First response: "I don't know what `items = items + [99]` does" and "I don't know the output style of
  `print("a,b,,c".split(","))`". No attempt at the other lines yet.
- Gap noted: **list `+` operator unknown** (syntax). The learner was unsure that `split` returns a list of strings shown as `['…']`.
- Gave Hint 1 (facts only, not the answer): `+` builds a *new* list; `split(sep)` returns a list of strings. Asked for a full attempt.
- Attempt (after hint): `[1,2,3,99]` / `[1,2,3,99]` / `error` / `['a', 'b', 'c']`
- Correct: `[1, 2, 3]` / `[1, 2, 3, 99]` / `[2, 3]` / `['a', 'b', '', 'c']`
- Results:
  - ✓ **Progress on aliasing**: correctly carried `append` through the parameter to the caller's list (P1 explanation absorbed).
  - ✗ **Rebinding vs mutation**: thought reassigning the local name (`items = ...`) also changes the caller's `a`.
  - ✓ `b` correct.
  - ✗ **Slice clamping missed a second time**, right after it was explained in P1. Retention/attention signal on a detail.
  - ✗ Missed the empty string between `,,`. List-of-strings output format ✓.
- Interim conclusion (Python fundamentals): genuinely beginner-level in Python semantics. Learns from explanation within a
  session (aliasing), but details don't stick after one exposure. Further predict-output drills would only confirm this.
  Moving on to **unaided implementation (I1)**, the key open question from Phase 0.

#### I1: unaided implementation, `top_senders` (2026-11-12, in progress)
- Language chosen: **Go** (`docs/main.go`).
- Help request 1: "why does this have an error". The code wrote the input as a Python-style literal
  `[["ali","hi"], ...]`, and the function signature `func top_senders([][]string)([]string)` had no parameter name and no `n`.
  - Gap: **Go composite literal syntax and parameter declaration syntax not recalled unaided**, after about 2 years of Go
    written with AI. This matches the Q7 self-report "doable with struggle (syntax/APIs)".
  - Help given: explained the compiler errors and showed the general syntax on *different* data. No solution logic given.
- Attempt 1 (`docs/main.go`): compiles and prints `[ali bob]` for the example. **Correct only by coincidence.**
  Verified by running a scratch copy with extra inputs (the learner's file was not modified):
  `n=1 → [sara]` (expected `[ali]`), `n=3 → []` (expected `[ali bob sara]`), `a=3,b=1,c=1, n=2 → []` (expected `[a b]`).
  Over 20 runs, n=2 printed `[ali bob]` 13× and `[bob ali]` 7×, because of random map iteration order.
  - ✓ Idiomatic map counting (`counts[name]++`, `make` with a size hint), `continue`, struct literal (after help).
  - ✗ **Requirement misread**: treated `n` as "senders with exactly n messages" instead of "top n". No ranking.
  - ✗ No sort and no tie-break. Output order depends on map iteration (nondeterministic).
  - ✗ Whitespace-only text not ignored (checked only `== ""`). Gap: `strings.TrimSpace`.
  - ✗ Tested only the given example, which happened to pass. Didn't try other inputs, so didn't find the failures.
  - The learner didn't report run/test details or time taken.
- Next: show the failing cases and ask for a fix (attempt 2). Hint 1 available on request.
- Learner report: attempt 1 took **about 5 min**. Used only Go docs, for one problem. **Declined attempt 2** and asked to move on.
  The reference solution was not shown. It is available on request.
- I1 interim reading: writes basic Go quickly (loops, maps, structs) but doesn't recall literal or signature syntax.
  Rushed reading of the spec. No habit of checking edge cases or testing beyond the given example. Sorting with a custom order
  (`sort.Slice`) is **not demonstrated** (not attempted), which is not the same as unable.

#### S1: SQL (2026-11-12)
- Before attempting, the learner self-reported: basic SQL only (SELECT/INSERT/UPDATE). **Struggles with JOINs, triggers and
  shared locks.** Would like exercises and help on normal queries as well.
  - This contradicts the Phase 0 code evidence (online migrations, generated columns, pt-osc). That evidence is
    re-classified as **AI-authored**, not learner skill.
- Adjusted the challenge down: (a) without a JOIN (GROUP BY/ORDER BY/LIMIT/date filter); (b) SQL injection; (c) a transaction scenario.
- The learner **skipped the written SQL** ("move from the query"). Writing SQL by hand is **Not assessed**. SQL skill rests on
  self-report only (basic CRUD).
- Format change: the learner prefers speed and options. The remaining domains get a quick conceptual round as options,
  with "not sure" offered so they don't have to guess. Per the spec, these results count **only toward A (conceptual)**,
  at Low–Medium confidence. B, C and D for those domains stay Not assessed until they're tested in practice during lessons.

#### Q-round: conceptual checks as options, "Not sure" offered (2026-11-12)
| Item | Answer | Result |
|---|---|---|
| SQL concatenation risk and fix | Injection; escape quotes manually | ½ Saw the risk. Wrong fix (placeholders unknown). |
| Crash between two DELETEs | "Both done anyway" | ✗ **Misconception about atomicity and autocommit.** Transactions not understood. |
| POST /users with a duplicate email | 409 Conflict | ✓ |
| Stale profile with a 1h TTL | Cache not invalidated on write | ✓ |
| Save + notify 3 services, one of them flaky | Save + publish event to a queue | ✓ |
| Retrying PUT after a timeout | Safe, PUT is idempotent | ✓ |
| Testing DB code fast and repeatably | Test DB or fake | ✓ |
| What `await` does in Python | "Starts a new thread" | ✗ Probably carried over the goroutine/thread mental model. |

## Assessment 1 — results (2026-11-12)

Scores are 0–4 per dimension. NA = Not assessed (this is **not** 0). Options items count only toward A, and only at Low confidence.
All code in the learner's repos is treated as AI-authored, so it supports no B, C or D scores.

| Competency | A Concept | B Implement | C Debug | D Real-world | Confidence | Evidence |
|---|---|---|---|---|---|---|
| Python fundamentals and data structures | 1 | NA | NA | NA | Medium (A) | P1/P2: aliasing learned during the session; rebinding, slice clamping (missed twice) and `split` wrong; `dict.get` counting ✓ |
| Python functions (mutation vs rebinding) | 1 | NA | NA | NA | Medium | P2 |
| Python OOP, typing, generators, decorators, context managers, packaging | NA | NA | NA | NA | Not assessed | Self-report: syntax only, Go-style OOP only |
| Python async | 0 | NA | NA | NA | Low | Q-round: thinks `await` starts a thread |
| General programming, unaided (Go) | 2 | 2 | 1 | NA | Medium | I1: map counting, loops and structs in about 5 min; needed help with literal and signature syntax; misread the spec (`n`); no sorting or tie-break; tested only the given example; declined attempt 2 |
| SQL basics (CRUD) | 1 | NA | NA | NA | Low | Self-report only; written SQL skipped |
| SQL JOINs, triggers, locking | NA | NA | NA | NA | Not assessed | Self-report: struggles with these |
| Transactions and atomicity | 0 | NA | NA | NA | Low | Q-round misconception |
| Security: SQL injection | 2 | NA | NA | NA | Low | Saw the risk, wrong fix |
| HTTP/REST semantics | 2 | NA | NA | NA | Low | 409 ✓, PUT idempotency ✓; self-report "designed REST APIs" (not verified) |
| Caching (Redis) | 2 | NA | NA | NA | Low | Invalidation scenario ✓ |
| Architecture: async/event-driven | 2 | NA | NA | NA | Low | Queue-based design ✓; daily exposure to a microservice codebase |
| Testing | 2 | NA | 1 | NA | Low | Concept ✓; never wrote tests (adminpanel tests were AI-written); I1 tested one example only |
| Git | NA | NA | NA | NA | Not assessed | Self-report: strong. History shows good commit hygiene, but AI-assisted. |
| Docker | NA | NA | NA | NA | Not assessed | Self-report: runs existing setups only |
| FastAPI, Pydantic, SQLAlchemy | NA | NA | NA | NA | Not assessed | No experience |

### Key findings
1. **Concepts are ahead of hands-on skill.** The learner picks good backend designs (queues, idempotency, cache invalidation,
   409) but can't yet implement unaided, even in Go after about 2 years of AI-written code.
2. **Main gaps:** Python language semantics, independent implementation, transactions, parameterized queries,
   JOINs and locking, writing tests, checking edge cases, Python async.
3. **Learning behavior:** absorbs a clear explanation within the session (aliasing fixed by P2), but details need repeating.
   Prefers speed and options. Skips written tasks when unsure. Reads specs quickly and sometimes misreads them.
   This is in tension with the stated "deep explanation first" preference. Design for **short explanation chunks, each followed
   by a small hands-on task with immediate feedback.**
4. **Not yet measured:** writing SQL, writing Python, debugging unfamiliar code. These will be measured inside lessons,
   not in more upfront tests.
