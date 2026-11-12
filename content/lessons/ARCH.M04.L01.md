---
{
  "id": "ARCH.M04.L01",
  "title": "Requirements, scope and numbers",
  "difficulty": "advanced",
  "minutes": 110,
  "prerequisites": ["ARCH.M03"],
  "objectives": [
    "Say what a design doc is for, and when a problem doesn't need one",
    "Turn a vague request into functional requirements, measurable non-functional requirements, goals and non-goals",
    "Make a back-of-the-envelope estimate (requests per second, peak, storage) and let it decide which components you need",
    "Spot requirements that hide the hard part of a design (double booking, ordering, 'real time')"
  ],
  "why": "You've added features to a system someone else designed. Designing from scratch starts one step earlier: deciding what the system must do, how much load it must carry, and what it explicitly won't do. Skip that step and you build Kafka for 1 request per second, or miss the one invariant that matters. This lesson starts a worked example you'll follow through the module: a meeting-room booking service.",
  "applications": [
    "Writing the first page of a design doc or RFC at work",
    "Pushing back on 'we need Kafka/Redis/microservices' with numbers",
    "Interview-style system design questions (a side benefit, not the goal)"
  ],
  "exercises": ["ARCH.M04.L01.E1"],
  "sources": [
    {
      "title": "Design Docs at Google",
      "url": "https://www.industrialempathy.com/posts/design-docs-at-google/",
      "version": "industrialempathy.com article (page fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["A design doc is the place to write down the trade-offs made in designing software", "Typical sections: context and scope, goals and non-goals, the actual design, alternatives considered, cross-cutting concerns", "Non-goals are things that could reasonably be goals but are explicitly chosen not to be; they aren't negated goals", "Skip the doc when the solution is obvious and has no real trade-offs", "Larger projects run about 10-20 pages; incremental changes can use a 1-3 page mini doc"]
    },
    {
      "title": "Redis docs: Redis cache-aside",
      "url": "https://redis.io/docs/latest/develop/use-cases/cache-aside/",
      "version": "redis.io docs (latest, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Caching reduces primary database load in proportion to the hit rate"]
    }
  ]
}
---
## 1. What a design doc is for

A design doc is written before the code, by the people who will build the system, and read by the people who will review, operate and extend it. The best one-line description comes from the "Design Docs at Google" article: the design doc is "*the place to write down the trade-offs* you made in designing your software."

The sections that article lists, which this module follows:

1. **Context and scope**: what's this about, briefly ("This isn't a requirements doc. Keep it succinct!").
2. **Goals and non-goals.**
3. **The actual design**: an overview, then the data model, the API and the important flows.
4. **Alternatives considered**: the article calls it "one of the most important" sections.
5. **Cross-cutting concerns**: security, privacy, observability.

We'll add one more that matters for backend systems: **failure modes** (L03).

**When not to write one:** the same article says to skip it when the solution is obvious and has no real trade-offs. "Add a column and an endpoint" doesn't need a doc. "Let people book rooms without double bookings across 40 sites" does. Length scales with the problem: the article mentions 10 to 20 pages for large projects and a 1 to 3 page "mini design doc" for smaller ones. Yours in this module will be the mini kind.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Which change most clearly deserves a design doc?",
  "options": ["Rename a field in an API response", "Add a `created_at` column to an existing table", "Let customers pay for bookings, with refunds and a third-party payment provider", "Fix a typo in an email template"], "answer": 2,
  "explanation": "Payments bring real trade-offs (consistency with bookings, retries, idempotency, failure handling) and several teams care about them. The others are obvious, one-step changes." }
```

## 2. The worked example: room booking

The request, as it would arrive from a product manager:

> "Our coworking company has 40 sites. Members should be able to book meeting rooms from the app, see what's free, and get a reminder before their meeting. No more double bookings: last month two teams showed up for the same room."

Turn it into **functional requirements**, each one testable:

- F1. A member can book a room for a time range, in 15-minute steps, at most 4 hours.
- F2. **Two confirmed bookings for the same room never overlap.** (This is the hard one. Write it down explicitly.)
- F3. A member can cancel their own booking; a cancelled booking frees the slot.
- F4. Anyone can see a room's free slots for a day.
- F5. The member gets a reminder 15 minutes before the booking starts.
- F6. Retrying a booking request (flaky mobile network) never creates two bookings.

Then **non-functional requirements**, with numbers, because "fast" and "reliable" can't be reviewed:

- N1. Booking: p99 under 500 ms. Availability page: p99 under 300 ms.
- N2. The availability view may be up to 30 s stale. A *booking* must always be checked against the true state.
- N3. A reminder may be up to 2 minutes late, and must not be lost or sent twice (duplicates are annoying, not dangerous).
- N4. 99.9% availability for booking during working hours.

Notice how N2 splits one feature into two consistency needs. That split is a design decision, and it comes straight from M02: cache the view, never the decision.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "Which is a well-written non-functional requirement?",
  "options": ["The system should be fast", "The system should scale", "The availability page returns within 300 ms at p99 under 12 requests/second", "The system should use Redis"], "answer": 2,
  "explanation": "It's measurable and states the load it applies to. 'Use Redis' is a solution, not a requirement, and 'fast' and 'scale' can't be checked." }
```

## 3. Goals and non-goals

The article's rule: non-goals are things that "could reasonably be goals", but you've decided not to do. They're not negations. "The system shouldn't crash" isn't a non-goal.

For the booking service:

- **Goals:** F1 to F6 for the 40 existing sites; the numbers in N1 to N4.
- **Non-goals:** recurring bookings; booking across sites in one request; payments; calendar sync (Google/Outlook); waitlists.

Non-goals protect the design. Recurring bookings alone would change the data model (a series plus exceptions) and the conflict check (every occurrence). Saying "not now" in writing lets you design the simple version properly, and tells the reviewer you considered it.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "'The booking service must not lose data' is a good non-goal to list.", "answer": false,
  "explanation": "That's a negated goal (a requirement in disguise), not a non-goal. A non-goal is a reasonable feature you're deliberately leaving out, like recurring bookings." }
```

## 4. Numbers before components

Before choosing components, estimate the load. Assumptions go in the doc as numbers a reviewer can challenge:

```python
import math

members = 5_000
views_per_member_per_day = 20       # availability page loads
bookings_per_day = 3_000
peak_factor = 10                     # 9:00 on Monday vs the daily average

daily_reads = members * views_per_member_per_day
avg_rps = daily_reads / 86_400
print(f"reads/day {daily_reads:,}  avg {avg_rps:.2f} rps  peak {math.ceil(avg_rps * peak_factor)} rps")
print(f"writes: avg {bookings_per_day / 86_400:.3f} rps  peak {math.ceil(bookings_per_day / 86_400 * peak_factor)} rps")

row_bytes = 200
years = 3
total = bookings_per_day * 365 * years * row_bytes
print(f"booking rows after {years} years: {bookings_per_day * 365 * years:,}  ~{total / 1e9:.2f} GB")
```

```console
$ python envelope.py
reads/day 100,000  avg 1.16 rps  peak 12 rps
writes: avg 0.035 rps  peak 1 rps
booking rows after 3 years: 3,285,000  ~0.66 GB
```

What the numbers decide:

- **12 reads per second at peak** is nothing for one PostgreSQL (or even SQLite) instance with an index on `(room_id, start)`. A cache isn't needed for *capacity*. You might still add one for latency, but now it's a choice you can justify, not a reflex. Caching reduces database load "proportionally to hit rate" (redis.io), and here there's little load to reduce.
- **One write per second at peak** means the conflict check can simply serialize writes per room, or even globally. No sharding, no distributed locks.
- **0.66 GB in three years** fits in memory on any server. No archiving plan needed in version 1.
- **Reminders**: about 3,000 a day, so a single worker polling a table once a minute is plenty. No Kafka needed for this load.

That last point isn't "Kafka is bad". It's that the numbers don't ask for it. Your messenger's fan-out to millions of users is a different problem with different numbers.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import math\n\nlinks_created_per_day = 200_000\nclicks_per_link_per_day = 50\npeak_factor = 8\n\nclicks = links_created_per_day * clicks_per_link_per_day\navg = clicks / 86_400\nprint(f\"{clicks:,} clicks/day, avg {math.ceil(avg)} rps, peak {math.ceil(avg * peak_factor)} rps\")",
  "answer": "10,000,000 clicks/day, avg 116 rps, peak 926 rps",
  "explanation": "10 million a day is about 115.7 per second on average; times 8 at peak is about 926. That's a different design conversation from 12 rps: now read caching and cheap redirects matter. (You'll design this system in L04.)" }
```

## 5. Requirements that hide the hard part

Some requirement words carry a whole design problem. Learn to stop at them:

| Phrase | Hidden question |
|---|---|
| "never double-booked" | What enforces it under concurrency: a constraint, a lock, a serialized write? |
| "real-time" | Within 100 ms? 2 s? 30 s? Each is a different architecture. |
| "exactly once" (reminders, payments) | Delivery is at-least-once (ARCH.M03); what deduplicates? |
| "in order" | Per user? Per room? Globally? |
| "always up to date" | Then it can't be cached, or it needs synchronous invalidation. Is that really required? |

```quiz
{ "id": "q5", "type": "explain", "label": "Design review",
  "prompt": "A draft design doc for the booking service says: 'Goals: fast, scalable, reliable booking. Architecture: FastAPI microservices (bookings, rooms, notifications) talking over Kafka, Redis for availability, PostgreSQL per service.' Write your review comments.",
  "model": "1) The goals aren't measurable: replace them with numbers (p99 latency, staleness allowed for availability, reminder lateness) and the expected load. 2) The architecture is chosen before the requirements: at about 12 reads and 1 write per second, three services with three databases and Kafka add failure modes (cross-service consistency, duplicate events) with no capacity benefit. Start with one service and one database, with clear internal layers. 3) The key invariant (no overlapping confirmed bookings for a room) isn't mentioned; the doc must say what enforces it. 4) There are no non-goals (recurring bookings? calendar sync?) and no alternatives considered. 5) Add failure modes: what happens when Redis or the reminder worker is down?",
  "explanation": "Requirements and numbers first; components must be justified by them." }
```

## 6. Your turn: estimate helpers

The exercise turns this section's arithmetic into four small, tested helpers. Most of the work is reading the spec: rounding direction, unit boundaries, and the exact comparison in `needs_cache`.

```exercise
ARCH.M04.L01.E1
```
