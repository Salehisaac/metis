---
{
  "id": "ARCH.M04.L02",
  "title": "Data model and API from requirements",
  "difficulty": "advanced",
  "minutes": 120,
  "prerequisites": ["ARCH.M04.L01"],
  "objectives": [
    "Derive tables, keys and constraints from functional requirements, and say which requirement each one serves",
    "Model time ranges as half-open intervals and write the overlap predicate",
    "Choose where an invariant is enforced (constraint, serialized transaction, application check) and show the race that the weaker choice allows",
    "Design the HTTP API for the use cases: resources, methods, status codes, idempotency keys"
  ],
  "why": "The data model is the part of a design that's hardest to change later, and the place where most invariants are either enforced or quietly lost. In the booking example, 'no double bookings' is decided by one SQL predicate and one transaction mode. Getting those right is the difference between a design that holds and one that worked in the demo.",
  "applications": [
    "Any reservation system: rooms, desks, appointments, rentals, tickets",
    "Translating a requirement like 'never twice' into a constraint or a transaction",
    "Reviewing API designs for status codes and retry safety"
  ],
  "exercises": ["ARCH.M04.L02.E1"],
  "sources": [
    {
      "title": "SQLite: Transaction (DEFERRED, IMMEDIATE and EXCLUSIVE)",
      "url": "https://www.sqlite.org/lang_transaction.html",
      "version": "SQLite docs (current); Python 3.12.3's bundled SQLite used for the demo",
      "verified": "2026-11-12",
      "claims": ["A DEFERRED transaction doesn't start until the database is first accessed; a read followed by a write upgrades if possible or returns SQLITE_BUSY", "IMMEDIATE starts a new write immediately, without waiting for a write statement", "BEGIN IMMEDIATE might fail with SQLITE_BUSY if another write transaction is active"]
    },
    {
      "title": "PostgreSQL docs: Range Types (8.17), Constraints on Ranges",
      "url": "https://www.postgresql.org/docs/current/rangetypes.html",
      "version": "PostgreSQL 18 (current) docs; PostgreSQL is not installed here",
      "verified": "2026-11-12",
      "claims": ["An exclusion constraint can express 'non-overlapping' on a range type", "With btree_gist, EXCLUDE USING GIST (room WITH =, during WITH &&) rejects overlapping ranges only for the same room", "[ is an inclusive lower bound and ) an exclusive upper bound; built-in discrete ranges use the canonical [) form"]
    },
    {
      "title": "sqlite3: transaction control (Cursor.execute, LEGACY_TRANSACTION_CONTROL)",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["In the default legacy mode, a transaction is implicitly opened before INSERT, UPDATE, DELETE or REPLACE when none is open"]
    },
    {
      "title": "Design Docs at Google",
      "url": "https://www.industrialempathy.com/posts/design-docs-at-google/",
      "version": "industrialempathy.com article (page fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["APIs and data storage are sketched in a design doc where they matter, without pasting complete definitions"]
    }
  ]
}
---
## 1. From requirements to tables

Recall the booking requirements from L01: book (F1), no overlaps (F2), cancel (F3), free slots (F4), reminders (F5), safe retries (F6). Walk through them and ask: **what must be stored, and what must the database guarantee?**

```sql
CREATE TABLE rooms (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE bookings (
    id INTEGER PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES rooms(id),
    member TEXT NOT NULL,
    start_ts INTEGER NOT NULL,
    end_ts INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed',      -- confirmed | cancelled
    idempotency_key TEXT NOT NULL UNIQUE
);
CREATE INDEX bookings_room_start ON bookings (room_id, start_ts);
```

Every column earns its place from a requirement:

| Decision | Requirement | Why this way |
|---|---|---|
| `start_ts`, `end_ts` as UTC instants | F1, F2 | Sites in different time zones; compare plain numbers. Convert to local time only for display. |
| `status` instead of `DELETE` | F3 | A cancelled booking stays as history, cancelling twice is harmless, and the reminder worker can see that a booking was cancelled. |
| `idempotency_key UNIQUE` | F6 | A retried request finds the original (ARCH.M03.L03). |
| Index `(room_id, start_ts)` | F2, F4 | The conflict check and the day view both filter by room and time. |
| No `reminders` table yet | F5 | Reminders can be derived from bookings by a worker (L03). Add a table only if you need to track sending. |

The "Design Docs at Google" article advises sketching the data model only where it matters, not pasting full definitions. In a real doc you'd show the `bookings` table and the constraint, and skip `rooms`.

## 2. Time ranges are half-open

A booking from 9:00 to 10:00 and one from 10:00 to 11:00 must both be allowed. Treat every range as **half-open, `[start, end)`**: it includes the start and excludes the end. PostgreSQL's docs use the same convention: `[` is an inclusive lower bound and `)` an exclusive upper bound, and its built-in discrete ranges use "the canonical form that includes the lower bound and excludes the upper bound; that is, `[)`."

With half-open ranges, two ranges overlap exactly when **each starts before the other ends**:

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "def overlaps(a_start, a_end, b_start, b_end):\n    return a_start < b_end and b_start < a_end\n\nprint(overlaps(9, 10, 10, 11), overlaps(9, 11, 10, 12), overlaps(9, 12, 10, 11), overlaps(10, 11, 9, 12))",
  "answer": "False True True True",
  "explanation": "Touching ranges don't overlap (10 < 10 is false). Partial overlap, 'a contains b' and 'b contains a' are all caught by the same two comparisons. No special cases needed." }
```

The common mistake is a list of special cases (`start between ...`, `end between ...`) that misses containment, or uses `<=` and forbids back-to-back meetings.

## 3. Where the invariant lives

F2 says confirmed bookings for a room never overlap. "Check, then insert" in application code looks right:

```python
CLASH = "SELECT COUNT(*) FROM holds WHERE spot = ? AND start_ts < ? AND ? < end_ts"
```

Here's what happens when two requests do it at the same moment. The demo uses a parking-spot table and two real SQLite connections, stepping through the interleaving by hand:

```console
$ python race.py
1) check, then insert (implicit transaction starts at the INSERT)
   holds: [(900, 960), (930, 990)]
2) BEGIN IMMEDIATE before the check
   B: database is locked (with a busy timeout, B would wait here)
   B sees a free slot? False
   holds: [(900, 960)]
```

In case 1 both requests checked before either inserted, so both "saw" a free spot: **double booked**. Python's sqlite3 (in its default mode) opens the transaction just before the `INSERT`, and SQLite's docs explain that a `DEFERRED` transaction "does not actually start until the database is first accessed". In case 2, `BEGIN IMMEDIATE` "causes the database connection to start a new write immediately, without waiting for a write statement". Request B can't start its check until A has committed, and then it sees A's hold.

Your options for enforcing an invariant, strongest first:

1. **A database constraint.** PostgreSQL can express "non-overlapping" directly with an exclusion constraint. Its docs show this exact example: with `btree_gist`, `EXCLUDE USING GIST (room WITH =, during WITH &&)` rejects overlapping ranges for the same room. Every code path is covered, including ones that forget to check. *Not runnable here: PostgreSQL isn't installed.*
2. **A serialized check-and-write in one transaction**: `BEGIN IMMEDIATE` on SQLite, or `SELECT ... FOR UPDATE` on a per-room row in PostgreSQL. Correct, as long as every writer uses it.
3. **An application check without serialization.** Case 1 above. It works in tests and fails under load.

A Redis lock is not on this list (ARCH.M02.A6): it expires on its own and the database isn't aware of it.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "Your service runs on PostgreSQL. Which way of enforcing 'no overlapping bookings per room' still holds if a future admin script inserts bookings directly with SQL?",
  "options": ["A check in the service's `book()` function", "A Redis lock per room", "An exclusion constraint on (room_id, time range)", "A unit test for overlaps"], "answer": 2,
  "explanation": "Only the constraint lives in the database itself, so every writer, including scripts and future services, is bound by it. The service check protects only the code path that calls it." }
```

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "In Python's sqlite3 default mode, running the conflict SELECT and the INSERT inside one `with conn:` block is enough to stop two concurrent requests from double-booking.", "answer": false,
  "explanation": "The implicit transaction starts at the INSERT, after the SELECT. Two connections can both run the SELECT first. Start with BEGIN IMMEDIATE so the check runs under the write lock." }
```

## 4. The API

Resources and operations follow the use cases, not the tables:

| Method and path | Use case | Success | Errors |
|---|---|---|---|
| `POST /rooms/{room_id}/bookings` with `Idempotency-Key` header | F1, F2, F6 | `201` with the booking (`200` with the same body on a retried key) | `404` room, `409` overlap, `422` invalid range or key reused for a different request |
| `POST /bookings/{id}/cancel` | F3 | `200` (also when already cancelled) | `404`, `403` not your booking |
| `GET /rooms/{room_id}/availability?date=2026-11-16` | F4 | `200` with the free slots | `404`, `422` |

Choices worth defending in review:

- **`409 Conflict` for an overlap.** The request was valid, but it conflicts with the current state of the resource. A `400` would tell the client its request was malformed.
- **Cancel is a `POST` to an action, not `DELETE`**, because the booking keeps existing with a new status. `DELETE /bookings/{id}` that leaves the row in place is a surprising contract. Both choices are defensible if documented; pick one.
- **The idempotency key is required** on the create call. Mobile clients retry, so F6 needs it.
- **Times in the API are ISO 8601 with an offset** (`2026-11-16T09:00:00+01:00`). Convert to UTC instants at the edge and store numbers.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "A client retries `POST /rooms/3/bookings` with the same Idempotency-Key after a timeout. The first request had succeeded. What should the response be?",
  "options": ["409 Conflict, because the slot is now taken", "The original booking, with a success status", "422, because the key was already used", "204 No Content"], "answer": 1,
  "explanation": "Same key, same request: return the stored result. The client can't tell whether the first attempt worked, and the key exists precisely to make the retry safe. 422 is for the same key with a different body." }
```

```quiz
{ "id": "q5", "type": "explain", "label": "Design review",
  "prompt": "A colleague proposes a different data model: a `slots` table with one row per room per 15-minute slot, `UNIQUE (room_id, slot_start)`, and a booking inserts one row per slot it covers. Compare it with the intervals-plus-transaction design. When would you pick it?",
  "model": "Slots: the invariant is a plain UNIQUE constraint that works in any database (no exclusion constraints, no BEGIN IMMEDIATE needed), and availability is a simple query. Costs: more rows (a 4-hour booking is 16 rows), slot size baked into the schema (moving to 10-minute slots means a migration), and a booking must insert all its rows in one transaction and clean them up on cancel. Intervals: one row per booking and flexible lengths, but the invariant needs an exclusion constraint (PostgreSQL) or serialized writes. Pick slots when slot size is truly fixed and you're on a database without range constraints, or when bookings are short and contention is high. Pick intervals for flexible durations on PostgreSQL. Either is fine at 1 write per second; write down why you chose.",
  "explanation": "Both designs can enforce the invariant; the alternatives section is where this comparison belongs." }
```

## 5. Your turn: implement `book()` from the design

The exercise gives you the schema above and the rules, in order. You implement `book()` and `cancel()`: validation, `BEGIN IMMEDIATE`, idempotency before conflicts, the half-open overlap check, and a clean rollback on every error.

```exercise
ARCH.M04.L02.E1
```
