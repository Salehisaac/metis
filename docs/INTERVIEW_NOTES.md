# Interview Notes (Phase 0)

Everything here is **self-reported**. It is not evidence of skill until confirmed by assessment.

## 2026-11-12

### Q1: Programming background
- Has worked on a messenger project in the `src` folder for about 2 years.
  - Observed: `/root/go/src` is a Go workspace (`go.work`). It contains `teamgram.io/`, `messenger-migration/`,
    `tgclient/`, `supportbot/` and others. Which folder is "the messenger", and the user's role in it, are not yet confirmed.
    Contents have not been inspected (no permission yet).
- Has Laravel (PHP) experience. Depth not yet known.
- Python: "basic understanding" (self-assessed).

### Q2: Messenger project and role
- Projects: `/root/go/src/teamgram.io/` and `/root/go/src/github.com/`.
- Role: did not create the original architecture or base structure. Improved existing code and built
  new features "a lot" over about 2 years, working as part of a team ("we").
- Read-only inspection permission: **granted for both folders** (read-only, no modifications).

### Observed (git history, read-only), 2026-11-12
Commits authored by the user (git identity "saleh"), compared with each repo's total:
- adminpanel 157/158, pathHandler 10/10, tgadmin 50/77. These repos are mostly or entirely the user's own.
- channels 244/836, teamgram-server 234/1549, teamgram 185/1288, enterprise 181/969, bots 143/491, stories 94/283.
- Smaller contributions: proto 36, ecosystem 20, teamcalls-server 17, channelcalls 12, redislock-gozero 2.
- Active from 2024-12 to 2026-11. This matches the "about 2 years" claim. Total: about 1,385 commits.
- The code itself is still under review (results go into the assessment evidence).

### Preference
- Wants questions asked as selectable options (multiple choice UI) rather than open-ended text.

### Q3: Areas touched and testing habits
- Has written or changed code in: database (SQL/schema), Redis cache, gRPC/RPC service calls, and queues/background jobs.
- Verifies features by **manual testing** (no habit of writing automated tests). This is a likely gap for the
  pytest-heavy track.

### Q4: Python, Laravel, goals
- Python: **syntax only** (has read or followed tutorials covering variables, loops, functions, lists and dicts).
  Has not written independent scripts.
- Laravel: personal or learning projects only, no production work.
- Goals: (1) Python backend job (Python/FastAPI), (2) architecture and design (designing systems themselves,
  not only adding features). Not selected: AI engineering, interview prep.

### Q5: Priority, time, learning style
- Priority: **Python backend job first**. Architecture skills develop alongside it.
- Study time: **5–10 hours/week**.
- Learning style: **deep explanation first** (wants to understand the "why" thoroughly before coding).

### Q6: HTTP, Docker, AI tools, Git
- HTTP/REST: says they have **designed REST APIs** (URLs, methods, status codes, error formats).
- Docker: **runs existing setups**, does not write Dockerfiles or compose files (but see the pathHandler Dockerfile below).
- AI tools: **"AI writes most code"**. The learner describes, the AI implements, the learner reviews and adjusts.
  ⚠ This matters most for the assessment. The code evidence below shows what was *shipped*, not what the learner can
  write unaided. Phase 1 must test independent ability without AI.
- Git: branches and merge conflicts, rebase and history editing, PR/MR review, debugging with history (blame/bisect).

### Q7: Unaided coding, AI rule, OOP
- A small Go feature (HTTP endpoint, MySQL, Redis) with no AI: **"doable with struggle"**. Knows what to do, but would
  often get stuck on syntax and APIs.
- **Agreed rule: no AI on exercises or assessments.** The learner writes all exercise code. The AI acts only as a mentor
  (hints and explanations) after the learner has made an attempt.
- OOP: **Go-style only** (structs, methods, interfaces, composition). Little class-based OOP, despite having used Laravel.

### Q8: Gate 0 and test authorship
- The learner confirmed the Phase 0 summary is accurate. **Gate 0 approved, 2026-11-12.**
- The 92 adminpanel test files were **AI-written**. No evidence yet that the learner can write tests themselves.

## Read-only code review (subagent, sampled; some claims spot-checked), 2026-11-12
Git authorship is matched on "saleh". The code is AI-assisted: adminpanel has 10 `Co-Authored-By: Claude` trailers,
and there are more in channels, teamgram-server and stories. Combined with the Q6 answer, **treat all code evidence as
"shipped with AI help". It is valid as evidence of understanding and judgment, and Low confidence for independent implementation.**

Shipped work (what exists):
- **adminpanel** (Go/go-zero/sqlx/JWT/bcrypt; 2026-08 to 10, 157/158 commits). Cloned from tgadmin and extended. Has documented
  layering rules (`internal/dao/dao.go`, "RPC vs direct-SQL" rule), a sort allow-list, LIKE escaping, limit caps,
  timing-safe login, an async batched audit writer, and transactions in places.
  Gaps: no authorization (any operator can ban), multi-step cross-service delete without compensation,
  goroutine started with `context.Background()`.
- **pathHandler**: a small stdlib HTTP service with parameterized SQL, correct 404/502 mapping, secrets from env. No tests.
- **tgadmin**: fixed its own security mistakes (payload-trusting JWT replaced with verified RSA; hardcoded OAuth secret removed).
- **channels/teamgram-server**: online MySQL migrations (generated column, scoped unique key, rollout order, pt-osc),
  Redis Lua for atomicity with TTL, invalidate-after-commit, gRPC/proto/TL changes, a security-sensitive TCP tunnel with
  an SSRF-style deny list and context/WaitGroup handling (9 test files).
  Gaps: swallowed errors (`authors, _ :=`), some multi-step writes without transactions, minor read-then-write races.
- **Testing**: many tests in adminpanel (92 files), but nearly all structural or pure-logic. No DB- or Redis-backed integration tests.
  This contradicts "manual testing only" from Q3, so they were possibly AI-generated. Clarify in assessment.
- **Languages in authored files**: Go, SQL, Lua, shell, proto/TL, YAML. **No Python or PHP** anywhere in the authored history.
- **Git hygiene**: mostly conventional commit subjects, many with bodies. Consistent with the Q6 self-report.

Initial estimates (provisional, to be tested in Phase 1, not scores):
- Backend concepts (SQL, caching, RPC, migrations, security patterns): likely strong understanding.
- Independent implementation in any language without AI: **unknown**. This is the key question.
- Python: near beginner (self-report plus no Python in history), but concepts should transfer from Go.
- Automated testing practice: weak.
- Architecture: has written design rationale and evaluates trade-offs. Has not designed a system from scratch unaided.
