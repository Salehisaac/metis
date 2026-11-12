---
{
  "id": "ARCH.M04.L03",
  "title": "Trade-offs, failure modes and decision records",
  "difficulty": "advanced",
  "minutes": 120,
  "prerequisites": ["ARCH.M04.L02"],
  "objectives": [
    "Write an 'alternatives considered' section that compares options on the criteria that matter for the requirements",
    "Build a failure-mode table: per dependency, what fails, what the user sees, how you detect it, what mitigates it",
    "Implement graceful degradation for an optional dependency while letting required-dependency errors surface",
    "Record a decision as an ADR (context, decision, status, consequences) and supersede it correctly"
  ],
  "why": "Your Go review found a cross-service delete with no plan for partial failure and errors swallowed with `_`. Both are failure modes nobody wrote down. Listing failure modes is the cheapest way to find those gaps before production does, and the alternatives section is where a reviewer checks that you chose rather than defaulted.",
  "applications": [
    "Design reviews: the 'what happens when X is down?' questions",
    "Incident follow-ups: was this failure mode in the doc? Was the mitigation built?",
    "Keeping decisions findable months later with ADRs in the repository"
  ],
  "exercises": ["ARCH.M04.L03.E1"],
  "sources": [
    {
      "title": "Design Docs at Google",
      "url": "https://www.industrialempathy.com/posts/design-docs-at-google/",
      "version": "industrialempathy.com article (page fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Alternatives considered is one of the most important sections: it shows why the chosen design is better", "Cross-cutting concerns such as security, privacy and observability must be addressed in every design"]
    },
    {
      "title": "Documenting Architecture Decisions",
      "url": "https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions",
      "version": "Michael Nygard, Cognitect blog (2011-11-15)",
      "verified": "2026-11-12",
      "claims": ["An ADR is a short text file capturing one significant decision", "Sections: Title, Context, Decision, Status, Consequences", "A reversed decision is kept and marked superseded"]
    },
    {
      "title": "fakeredis documentation",
      "url": "https://fakeredis.readthedocs.io/en/latest/",
      "version": "fakeredis docs (latest); installed fakeredis 2.40.0",
      "verified": "2026-11-12",
      "claims": ["Connection errors can be simulated by setting the server's connected attribute to False"]
    },
    {
      "title": "microservices.io: Pattern: Transactional outbox",
      "url": "https://microservices.io/patterns/data/transactional-outbox.html",
      "version": "microservices.io (Chris Richardson), undated page",
      "verified": "2026-11-12",
      "claims": ["The message relay might publish a message more than once"]
    }
  ]
}
---
## 1. Alternatives considered

The "Design Docs at Google" article calls this section "one of the most important ones", because it shows why the chosen design is better than the others. A good alternatives section compares options **on the criteria the requirements care about**, not on general pros and cons.

For the booking service, three decisions deserve a row each:

| Decision | Options | Criteria from the requirements | Choice |
|---|---|---|---|
| Enforce "no overlaps" (F2) | App check / serialized transaction / exclusion constraint / slots table with UNIQUE | Correct under concurrency; works on our database; flexible durations | Exclusion constraint on PostgreSQL; serialized transaction where we only have SQLite (L02) |
| Availability view (F4, N2: 30 s stale OK) | Query every time / cache-aside with 30 s TTL / precomputed table | 12 rps peak; p99 300 ms | Query plus index is enough for capacity; cache-aside with TTL 30 *only* if latency measurements say so |
| Reminders (F5, N3: 2 min late OK, never lost) | BackgroundTasks timer / in-process scheduler / worker polling the table / message queue with delayed delivery | Survives restarts; at-least-once; 3,000 a day | A worker polling `bookings` every minute, with a `reminded_at` column |

Each choice points back to a requirement. "We picked Redis because it's fast" doesn't; "we skip the cache because 12 rps doesn't need it, and N2 lets us add one later without changing the API" does.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Why is a BackgroundTasks timer the wrong choice for booking reminders?",
  "options": ["It can't send emails", "It lives in the web process's memory, so a deploy or crash loses every pending reminder, and N3 says reminders must not be lost", "It's too slow for 3,000 reminders a day", "FastAPI forbids sleeping in background tasks"], "answer": 1,
  "explanation": "The requirement 'never lost' rules out in-process scheduling (ARCH.M03.L01). The reminder must be derivable from durable state, so a worker can pick it up after any restart." }
```

## 2. The reminder worker, briefly

The chosen design: every minute, a worker selects confirmed bookings that start within the next 15 minutes and haven't been reminded, sends each reminder, and sets `reminded_at`. It's the outbox's relay idea, with the bookings table itself as the outbox:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import sqlite3\n\nconn = sqlite3.connect(\":memory:\")\nconn.execute(\"CREATE TABLE bookings (id INTEGER, start_ts INTEGER, status TEXT, reminded_at INTEGER)\")\nconn.executemany(\"INSERT INTO bookings VALUES (?, ?, ?, ?)\", [\n    (1, 600, \"confirmed\", None),\n    (2, 900, \"confirmed\", None),\n    (3, 901, \"confirmed\", None),\n    (4, 300, \"cancelled\", None),\n    (5, 500, \"confirmed\", 450),\n    (6, 0, \"confirmed\", None),\n])\nnow = 0\ndue = conn.execute(\n    \"SELECT id FROM bookings WHERE status = 'confirmed' AND reminded_at IS NULL \"\n    \"AND start_ts > ? AND start_ts <= ? ORDER BY id\",\n    (now, now + 900),\n).fetchall()\nprint([row[0] for row in due])",
  "answer": "[1, 2]",
  "explanation": "1 and 2 start within the next 900 s (2 is exactly on the boundary, which `<=` includes). 3 is one second too late, 4 is cancelled, 5 was already reminded, and 6 has already started (`start_ts > now` is false)." }
```

Its failure behaviour is already designed by ARCH.M03: if the worker crashes after sending but before setting `reminded_at`, the reminder goes out twice. That's at-least-once delivery, which microservices.io notes for the outbox relay too ("might publish a message more than once"). N3 says duplicates are acceptable, so no deduplication table is needed. Sending an idempotency key (the booking id) to the email provider would reduce duplicates further, if the provider supports it.

## 3. The failure-mode table

For each dependency, write one row per way it can fail. The columns force the questions a reviewer will ask:

| Dependency and failure | What the user sees | How we detect it | Mitigation |
|---|---|---|---|
| Database down | Booking and availability fail (503) | Health check, error rate alert | None in v1: it's the source of truth. Managed DB with failover. |
| Redis down or refusing connections | Availability is slower, still correct | Warning log plus "degraded" metric | Fall back to the database (this lesson's exercise) |
| Redis slow (hangs) | Every availability request waits for the timeout | Latency alert | Short client socket timeouts turn "slow" into "error", then fall back |
| Reminder worker down | Reminders late, then missed once their start time passes | Alert on the age of the oldest due, unreminded booking | Restart the worker; it catches up because state is in the table |
| Email provider down | Reminders not delivered | Send-error rate | Retry with backoff until the start time (ARCH.M03.L03), then give up and log |
| Client retries a booking | Nothing (same booking returned) | — | Idempotency key (L02) |
| Two requests book the same slot | One gets 409 | 409 rate metric | Serialized transaction or exclusion constraint (L02) |

Two rules make the table useful:

1. **Separate required from optional dependencies.** The database is required: without it there is no correct answer, so fail clearly. Redis is optional for this design: losing it must cost speed, not correctness. That distinction decides which exceptions you catch (and log) and which you let through.
2. **Every "mitigation" needs a "detection".** A fallback nobody notices is how a cache outage turns into a database outage a week later. The degraded path must log or count.

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "During a Redis outage the availability endpoint keeps working by falling back to the database, but nobody knows Redis is down. A week later, peak traffic overloads the database. Which column of the failure-mode table was missing?",
  "options": ["What the user sees", "Detection", "Mitigation", "Dependency"], "answer": 1,
  "explanation": "The mitigation (fallback) worked, which is exactly why the outage stayed invisible. Without a warning log, metric or alert on the degraded path, the system ran without its cache until the next peak." }
```

## 4. Decision records (ADRs)

A design doc captures a design at one moment. Decisions keep changing afterwards. Michael Nygard's **architecture decision records** keep them findable: "a short text file" per significant decision, with five sections: **Title**, **Context** ("the forces at play"), **Decision**, **Status** (proposed, accepted, ...), and **Consequences** ("the resulting context, after applying the decision").

```text
# ADR 3: Enforce no-overlap with a serialized SQLite transaction

Status: Accepted (2026-11-16)

Context: F2 forbids overlapping confirmed bookings per room. v1 runs on SQLite
(one small server, ~1 write/s at peak). SQLite has no exclusion constraints.

Decision: book() starts with BEGIN IMMEDIATE and runs the idempotency lookup,
the overlap check and the insert inside that one write transaction.

Consequences: All writes are serialized (fine at 1 write/s). Every code path
that inserts bookings must go through book(). Moving to PostgreSQL should
replace this with an exclusion constraint (new ADR).
```

When the team moves to PostgreSQL, you don't edit ADR 3. Nygard: "If a decision is reversed, we will keep the old one around, but mark it as superseded." ADR 7 explains the new decision, and ADR 3's status becomes "Superseded by ADR 7". The history of *why* stays readable.

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "When a decision recorded in an ADR changes, you should update that ADR's Decision section so the repository only shows current decisions.", "answer": false,
  "explanation": "Keep the old ADR and mark it superseded, with a pointer to the new one. Knowing that something was once decided, and why it changed, is the value of the record." }
```

## 5. Cross-cutting concerns

The article lists "security, privacy, and observability" as concerns every design must address. For the booking service, one line each is enough in a mini doc:

- **Security:** only the booking's member (or an admin) can cancel it, and the endpoint returns 403 otherwise. Room ids aren't secret; booking ids are checked against the member.
- **Privacy:** availability shows free slots, not who booked the room. Member names appear only to staff.
- **Observability:** metrics for booking latency, 409 rate, degraded availability responses and the age of the oldest due reminder. Logs carry the booking id.

```quiz
{ "id": "q5", "type": "explain", "label": "Design review",
  "prompt": "A failure-mode table in a draft says: 'Redis down → we catch Exception around all Redis and database calls in the availability endpoint and return an empty list of free slots, so the page never errors.' Review that mitigation.",
  "model": "It's wrong in three ways. (1) An empty list means 'fully booked', so users see false information instead of an error: degrade to the database, not to a fake answer. (2) Catching Exception around the database calls hides the required dependency's failure; database errors should surface as a clear 503. (3) Nothing is logged or counted, so the outage is invisible (no detection). Fix: catch only redis.RedisError around the cache calls, log a warning and count it, answer from the database, and let database errors propagate.",
  "explanation": "Degrade to a slower correct answer, never to a fast wrong one, and make the degradation visible." }
```

## 6. Your turn: implement one row of the table

The exercise implements the "Redis down" row: compute free slots from bookings (a pure function with the edge cases from L02), cache them for 30 s, and fall back to the database when Redis fails, reporting `'db-degraded'` and logging it. Database errors must still surface. The tests simulate the outage with fakeredis.

```exercise
ARCH.M04.L03.E1
```
