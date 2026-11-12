---
{ "id": "ARCH.M04.A", "module": "ARCH.M04", "title": "ARCH.M04 module assessment: designing from scratch", "minutes": 30 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. The main evidence for this module is your design doc (ARCH.M04.L04.E1) and its mentor review; these questions check the reasoning behind it.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "import math\n\nviews_per_day = 3_000_000\npeak_factor = 6\navg = views_per_day / 86_400\nprint(math.ceil(avg), math.ceil(avg * peak_factor))",
  "answer": "35 209",
  "explanation": "3,000,000 / 86,400 = 34.7 rps on average, rounded up to 35; at a 6x peak, 208.3, rounded up to 209. Estimates round up." }
```

```quiz
{ "id": "a2", "type": "choice",
  "prompt": "Which is a non-goal (rather than a goal or a negated goal)?",
  "options": ["The service must not lose bookings", "Recurring weekly bookings are out of scope for v1", "Booking p99 under 500 ms", "The service should be secure"], "answer": 1,
  "explanation": "A non-goal is a reasonable feature deliberately left out. 'Must not lose bookings' is a requirement phrased negatively; the others are goals." }
```

```quiz
{ "id": "a3", "type": "output",
  "prompt": "What does this print?",
  "code": "bookings = [(9, 10), (11, 12)]\nrequests = [(10, 11), (9, 9.5), (8, 13), (12, 13)]\nprint([not any(s < e2 and s2 < e for s2, e2 in bookings) for s, e in requests])",
  "answer": "[True, False, False, True]",
  "explanation": "Half-open intervals: [10, 11) fits between the two bookings and [12, 13) starts when the second ends. [9, 9.5) overlaps the first and [8, 13) contains both." }
```

```quiz
{ "id": "a4", "type": "truefalse",
  "prompt": "In a failure-mode table, a fallback that hides an outage from users makes a 'Detection' entry unnecessary.", "answer": false,
  "explanation": "A silent fallback is exactly what needs detection: otherwise the system runs degraded (for example without its cache) until the next peak turns it into a real outage." }
```

```quiz
{ "id": "a5", "type": "explain", "label": "Design review",
  "prompt": "Design a 'library book holds' feature in five bullets of a mini design doc: members place a hold on a book; when a copy is returned, the next member in line gets 48 hours to pick it up and is notified by email. Cover: the invariant, the data model key decision, where the transaction is, how the notification is made reliable, and one failure mode with detection.",
  "model": "Invariant: a returned copy is offered to exactly one member at a time, in hold order. Data model: holds(id, book_id, member_id, created_at, status: waiting/offered/fulfilled/expired, offered_until), with a unique constraint so a member holds a book once, and at most one 'offered' hold per copy, enforced by a conditional UPDATE. Transaction: the return use case marks the copy returned, picks the oldest waiting hold, sets it to offered with offered_until = now + 48 h, and inserts an outbox row, all in one transaction (BEGIN IMMEDIATE on SQLite). Notification: a relay sends the email from the outbox with retries and backoff; duplicates are acceptable, or deduplicate by hold id. Expiry: a worker moves expired offers to 'expired' and offers the next hold (idempotent). Failure mode: relay down means emails aren't sent while the 48 h clock runs; detect with an alert on the age of the oldest pending outbox row; mitigation: restart, and optionally extend offered_until when the notification was late.",
  "explanation": "Invariant, transaction boundary, durable side effect, failure with detection: the same four questions every design gets." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Design review",
  "prompt": "A reviewer comments on your booking design: 'Why not put availability in Redis and check overlaps there? It's faster than the database.' Write your reply.",
  "model": "The overlap check enforces our core invariant (no double bookings), so it must run against the source of truth inside the same transaction as the insert: an exclusion constraint on PostgreSQL, or BEGIN IMMEDIATE on SQLite. Redis isn't transactional with our database: a check in Redis followed by an insert in the database is a race, and a stale or lost Redis entry would allow double bookings. Speed isn't a constraint here either: writes peak at about 1 per second, and the database check is an indexed lookup. Redis may be used for the availability view (staleness of up to 30 s is allowed), but never for the booking decision. I'd revisit this only if booking latency missed its 500 ms goal, and then I'd look at the database query first.",
  "explanation": "Decisions read the source of truth; caches serve views. Tie the answer to the requirement and the numbers." }
```
