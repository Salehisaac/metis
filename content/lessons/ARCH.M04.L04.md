---
{
  "id": "ARCH.M04.L04",
  "title": "Writing and defending a design doc",
  "difficulty": "advanced",
  "minutes": 150,
  "prerequisites": ["ARCH.M04.L03"],
  "objectives": [
    "Assemble a complete mini design doc (requirements, estimates, data model, API, alternatives, failure modes, cross-cutting concerns) in under 1200 words",
    "Review a design doc with a checklist and write specific, requirement-based comments",
    "Find the flaw in short design excerpts: missing invariants, unjustified components, fake degradation, wrong status codes",
    "Respond to review comments by tracing your choice back to a requirement, or changing it"
  ],
  "why": "This is the outcome of the whole ARCH course: design a system you weren't handed, write it down, and defend it in review. Everything from the earlier modules shows up as a review question: where the transaction lives, what the cache can serve stale, what happens on a duplicate delivery. Your capstone (PRJ-05) is a system you design yourself, so a document like this is its natural first step.",
  "applications": [
    "Proposing a feature or service at work with a reviewable doc",
    "Reviewing colleagues' designs with concrete questions instead of taste",
    "Starting the capstone, PRJ-05"
  ],
  "exercises": ["ARCH.M04.L04.E1"],
  "sources": [
    {
      "title": "Design Docs at Google",
      "url": "https://www.industrialempathy.com/posts/design-docs-at-google/",
      "version": "industrialempathy.com article (page fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["A design doc records the trade-offs made in designing the software", "Sections: context and scope, goals and non-goals, the actual design, alternatives considered, cross-cutting concerns", "Smaller projects can use a 1-3 page mini design doc", "A doc that only describes how something will be built, without trade-offs, is better replaced by writing the code"]
    },
    {
      "title": "RFC 9110: HTTP Semantics, 15.4 Redirection 3xx",
      "url": "https://www.rfc-editor.org/rfc/rfc9110.html",
      "version": "RFC 9110 (June 2022); section text read from the plain-text RFC",
      "verified": "2026-11-12",
      "claims": ["301 means the resource has a new permanent URI; a 301 response is heuristically cacheable", "302 means the resource resides temporarily under a different URI and the client ought to keep using the original URI"]
    },
    {
      "title": "Documenting Architecture Decisions",
      "url": "https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions",
      "version": "Michael Nygard, Cognitect blog (2011-11-15)",
      "verified": "2026-11-12",
      "claims": ["Decisions are recorded with context, decision, status and consequences; reversed decisions are kept and marked superseded"]
    }
  ]
}
---
## 1. The whole doc, assembled

L01 to L03 built the room-booking design piece by piece. Here it is as one mini design doc: the shape your own doc should take. It's deliberately short. The "Design Docs at Google" article describes a "mini design doc" of 1 to 3 pages for smaller projects.

````markdown
# Design: Meeting-room booking

## Context and scope
Members of a coworking company (40 sites, ~400 rooms) book meeting rooms in the app. Double bookings
happened last month. This doc covers booking, cancelling, the availability view and reminders.

## Goals
- No two confirmed bookings for a room overlap, under any concurrency (F2).
- Booking p99 < 500 ms; availability p99 < 300 ms; availability may be 30 s stale.
- Reminders 15 min before start, at most 2 min late, never lost (duplicates acceptable).
- A retried booking request never creates a second booking.

## Non-goals
- Recurring bookings, cross-site bookings, payments, calendar sync, waitlists.

## Estimates
- Reads: 5,000 members x 20 views = 100k/day: ~1.2 rps average, 12 rps peak (x10 at 9:00).
- Writes: 3,000 bookings/day: ~1 rps at peak. Storage: ~0.66 GB in 3 years.
- So: one database, no sharding, no message broker; a cache is optional (latency only).

## Data model
bookings(id, room_id, member, start_ts, end_ts, status, idempotency_key UNIQUE),
half-open [start_ts, end_ts) in UTC, index (room_id, start_ts). No-overlap: PostgreSQL exclusion
constraint (room_id WITH =, range WITH &&); on SQLite, BEGIN IMMEDIATE around check + insert.

## API
- POST /rooms/{id}/bookings (Idempotency-Key): 201 | 200 same key | 404 | 409 overlap | 422
- POST /bookings/{id}/cancel: 200 (idempotent) | 403 | 404
- GET /rooms/{id}/availability?date=...: 200 free 15-min slots

## Alternatives considered
- Slots table with UNIQUE(room, slot): simpler constraint, but fixed slot size in the schema;
  rejected because durations vary and PostgreSQL can enforce ranges directly.
- Reminders via BackgroundTasks timers: rejected because a deploy loses them (goal: never lost).
- Cache-aside for availability: deferred because 12 rps needs no cache; add with TTL 30 s if p99 needs it.

## Failure modes
| Dependency and failure | What the user sees | Detection | Mitigation |
|------------------------|--------------------|-----------|------------|
| Database down | Booking fails (503) | Error-rate alert | Managed failover; nothing else can answer |
| Redis down (if added) | Availability slower | Degraded metric | Fall back to the database |
| Reminder worker down | Reminders late | Oldest-due-reminder age alert | Restart; state is in the table |
| Email provider down | Reminders not delivered | Send-error rate | Retry with backoff until start time |

## Cross-cutting concerns
Security: only the booker or an admin cancels. Privacy: availability hides who booked.
Observability: booking latency, 409 rate, reminder lag.
````

Notice what's **not** there: class diagrams, full SQL for every table, code. The article suggests avoiding complete definitions and linking to prototypes instead. A design doc earns its length with decisions and their reasons.

## 2. How to review a design doc

Read it once for understanding, then go through this checklist. Each "no" becomes a comment that names the requirement it threatens.

1. **Goals:** measurable (numbers, percentiles), and do the non-goals rule out the expensive features explicitly?
2. **Numbers:** are the components justified by the estimates? (Kafka for 1 rps? No cache at 900 rps with a 50 ms goal?)
3. **Invariants:** for each "never" and "exactly once" in the goals, what enforces it, and does it hold under concurrency and retries?
4. **Transactions:** where does each multi-step write's transaction start and end? What happens to side effects (cache, events, emails) relative to the commit?
5. **Staleness:** what can be served stale, for how long, and what bounds it?
6. **Failure modes:** a row for every dependency, each with detection. Required vs optional dependencies separated.
7. **Alternatives:** at least one serious alternative per major decision, decided by a requirement.
8. **API:** status codes match the semantics; retries are safe where clients retry.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Reviewing a ticket-sales design: goals say 'never sell more tickets than seats'. The design checks `sold < capacity` in Python, then inserts the ticket, in the default sqlite3 transaction mode. Which comment matters most?",
  "options": ["Consider renaming `sold` to `tickets_sold`", "The capacity check is a read-then-write race: two buyers can both pass it. Enforce it with a conditional UPDATE on a counter or a serialized transaction", "Add a cache for the event page", "Use 422 instead of 400 for validation errors"], "answer": 1,
  "explanation": "The goal is an invariant, and the design doesn't enforce it under concurrency. That's a correctness bug in the core requirement; the others are minor or unrelated." }
```

## 3. Find the flaw

Short excerpts from design docs. Each has one serious problem. These are the questions you'll be asked about your own doc.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "A link-shortener doc says '6-character base62 codes are plenty'. With 200,000 new links a day, how many years until the code space is used up? What does this print?",
  "code": "codes = 62 ** 6\nper_year = 200_000 * 365\nprint(f\"{codes:,}\", codes // per_year)",
  "answer": "56,800,235,584 778",
  "explanation": "About 57 billion codes last 778 years at that rate, so 6 characters are enough for capacity. The real question for random codes is collisions: as the table fills, more random picks hit existing codes, so the design must retry on a unique-constraint error." }
```

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "A shortener whose links can expire should answer redirects with 301, because RFC 9110 defines 301 as the standard redirect for short links.", "answer": false,
  "explanation": "RFC 9110 defines 301 as a new *permanent* URI, and a 301 response is heuristically cacheable, so browsers may keep redirecting after the link expires (and the server never sees those clicks). 302 says the resource is only temporarily elsewhere and the client should keep using the original URI." }
```

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "A failure-mode table row reads: 'Payment provider down | User sees 'order placed' | — | Orders are saved; we'll charge later.' What's the most important missing piece?",
  "options": ["The user-facing message should be friendlier", "Detection and the 'charge later' mechanism: nothing records that a charge is pending or retries it, so orders may never be charged", "The row should be split into two rows", "Payment providers never go down"], "answer": 1,
  "explanation": "'Charge later' is a durable-work requirement (outbox or pending-charges table plus a worker with retries and idempotency keys), and without detection nobody knows charges are piling up. As written, it's a plan to lose money silently." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Design review",
  "prompt": "A doc for a 'notify followers when someone posts' feature says: 'When a user posts, the API inserts the post and then, in the same request, inserts one notification row per follower (users have up to 2 million followers) inside the same transaction.' Find the flaw and propose a fix.",
  "model": "One request doing up to 2 million inserts in one transaction: the request takes minutes and times out, the transaction holds locks and grows huge, and a failure rolls back the post itself. Fan-out doesn't belong on the request path. Fix: commit the post plus one outbox event (post.created) in a small transaction; a worker consumes it and creates notifications in batches, idempotently (keyed by post id and follower id), with retries. Delivery becomes eventually consistent. For huge accounts, consider fan-out on read (followers pull recent posts from the accounts they follow) instead of writing millions of rows. This is the same queue-based fan-out you suggested in your assessment, now with the outbox and idempotency it needs.",
  "explanation": "Keep the request's transaction small; push fan-out to a durable, idempotent worker." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Design review",
  "prompt": "A doc's alternatives section says only: 'We considered PostgreSQL and MongoDB and chose PostgreSQL because it's more reliable.' Rewrite the comment you'd leave, and say what a good version of this section would contain.",
  "model": "Comment: 'More reliable' isn't tied to a requirement and isn't checkable. Which requirement decides it? For example: we need a uniqueness or no-overlap invariant enforced by the database (unique and exclusion constraints), multi-row transactions for X, and the team already runs PostgreSQL. A good section names each major decision (storage, how the invariant is enforced, sync vs async processing), lists one or two real alternatives, compares them on the criteria from the goals (consistency, latency, operability, cost) and states what would make you revisit the choice.",
  "explanation": "Alternatives are decided by requirements; 'better' without a criterion is preference." }
```

## 4. Defending your design in review

Review comments come in three kinds. Answer each differently:

- **"You missed X."** (a failure mode, a race). Thank them, fix the doc, and if it changes a decision, record it (an ADR, or a "Changes after review" line).
- **"Why not Y?"** Trace your choice to a requirement: "We chose polling over Kafka because 3,000 reminders a day doesn't need a broker, and the bookings table already holds the state (Estimates, Alternatives)." If you can't trace it, the reviewer may be right.
- **"I'd prefer Z."** If Z and your choice both meet the requirements, say so, keep yours, and move on. Not every disagreement needs a winner.

Also write down **what would make you change your mind**: "If peak reads exceed 500 rps or p99 misses 300 ms, add cache-aside for availability." It turns a debate into a condition you can measure.

## 5. Your turn: your own design doc

The exercise brief is a **link shortener with daily click counts** for a marketing team (L01's quiz numbers: 10 million clicks a day). It's a new domain, so there's nothing to copy from the booking doc above, only the shape. Fill in `DESIGN.md` from the template.

- The tests check **completeness**: all sections in order, no TODO left, goals and non-goals as lists, numbers in the estimates, a schema with a key, at least two endpoints and a redirect status, reasoned alternatives, a failure-mode table and the cross-cutting concerns, all within 1200 words.
- The **mentor review** checks **quality**, with section 2's checklist. Bring the doc to a mentor session, and be ready for "why?" on every decision.

```exercise
ARCH.M04.L04.E1
```
