---
{
  "id": "DB.M05.L03",
  "title": "Measuring: timeit on generated data, and what indexes cost on writes",
  "difficulty": "intermediate",
  "minutes": 80,
  "prerequisites": ["DB.M05.L02"],
  "objectives": [
    "Generate reproducible test data at realistic volume with a seeded random.Random and one transaction",
    "Time a query with timeit.repeat, report the minimum per call, and say why the minimum",
    "Measure what each extra index costs on inserts",
    "Show with numbers when an index makes a query slower (low selectivity) and decide whether to keep it"
  ],
  "why": "An index is a trade: faster reads for slower writes and more storage. EXPLAIN tells you the shape of a plan, not what it costs. This lesson's outcome is the module's goal: add an index you can justify with a measurement, not a hunch.",
  "applications": [
    "Writing the 'before/after' numbers into a migration's pull request",
    "Rejecting an index that helps nobody but slows every insert",
    "Load-testing a schema locally before production data exists"
  ],
  "exercises": ["DB.M05.L03.E1"],
  "sources": [
    {
      "title": "timeit: Measure execution time of small code snippets",
      "url": "https://docs.python.org/3.12/library/timeit.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["timeit.repeat returns a list of totals, one per round", "Use the min() of the repeat results; higher values are usually other processes interfering", "The default timer is time.perf_counter()", "timeit temporarily turns off garbage collection during timing"]
    },
    {
      "title": "PostgreSQL 18 Documentation: Chapter 11. Indexes",
      "url": "https://www.postgresql.org/docs/current/indexes.html",
      "version": "PostgreSQL 18 (docs 18.7); concept only, not run here",
      "verified": "2026-11-12",
      "claims": ["Indexes let the database find rows much faster", "Indexes add overhead to the database system as a whole, so they should be used sensibly"]
    },
    {
      "title": "The SQLite Query Optimizer Overview",
      "url": "https://www.sqlite.org/optoverview.html",
      "version": "SQLite docs, page updated 2025-05-31; verified locally with SQLite 3.45.1",
      "verified": "2026-11-12",
      "claims": ["ANALYZE gathers statistics into sqlite_stat tables to help the planner estimate costs", "The statistics are not updated automatically as data changes"]
    },
    {
      "title": "sqlite3: DB-API 2.0 interface for SQLite databases",
      "url": "https://docs.python.org/3.12/library/sqlite3.html",
      "version": "Python 3.12 (installed 3.12.3, SQLite 3.45.1)",
      "verified": "2026-11-12",
      "claims": ["Using the connection as a context manager commits on success and rolls back on an exception"]
    }
  ]
}
---
## 1. A plan shows the shape, not the cost

From L01 and L02 you can tell a SCAN from a SEARCH. That doesn't yet tell you whether the difference *matters*:

- A SCAN of 300 rows takes microseconds. An index on a tiny table only costs writes.
- A SEARCH that still visits half the table can be **slower** than a plain scan (section 5).
- Every index costs time on every INSERT, UPDATE and DELETE (section 4). The PostgreSQL docs put it plainly: indexes "add overhead to the database system as a whole, so they should be used sensibly."

So the module's rule: **plan → measure at realistic volume → index → re-measure (reads and writes) → keep or drop.** You need data and a stopwatch.

```quiz
{ "id": "q1", "type": "truefalse",
  "prompt": "If EXPLAIN QUERY PLAN changes from SCAN to SEARCH after you add an index, the query is guaranteed to be faster.", "answer": false,
  "explanation": "SEARCH only says a subset of rows is visited through an index. If that subset is most of the table, the extra index lookups can make it slower than a scan. Only a measurement tells you." }
```

## 2. Realistic data, reproducibly

You can't measure on the 5 rows from your tests. Generate a few hundred thousand, and make the generator **deterministic**, so a before/after comparison runs on the same data every time:

```python
import random
import sqlite3
import timeit

conn = sqlite3.connect(":memory:")
conn.execute("""CREATE TABLE messages (
    id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, sender_id INTEGER NOT NULL,
    body TEXT NOT NULL, created_at TEXT NOT NULL)""")

rng = random.Random(42)                      # fixed seed: same data every run
rows = [
    (rng.randrange(1, 1001),                 # 1000 chats
     rng.randrange(1, 5001),                 # 5000 users
     f"message {i}",
     f"2026-{rng.randrange(1, 13):02d}-{rng.randrange(1, 29):02d}")
    for i in range(200_000)
]
with conn:
    conn.executemany(
        "INSERT INTO messages (chat_id, sender_id, body, created_at) VALUES (?, ?, ?, ?)", rows)
```

Three choices worth copying:

- **`random.Random(42)`**, a private generator with a seed, not the global `random.seed()`. Same rows on every run, and nothing else's randomness is disturbed. It's Go's `rand.New(rand.NewSource(42))`.
- **Shape the data like production.** 200 messages per chat on average is a different problem from 200,000 messages in one chat. Pick the distribution you expect.
- **One transaction** (`with conn:` from DB.M03). Committing each of 200,000 rows separately would take far longer than the queries you want to measure.

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import random\na = random.Random(3)\nb = random.Random(3)\nprint([a.randint(1, 9) for _ in range(3)] == [b.randint(1, 9) for _ in range(3)])",
  "answer": "True",
  "explanation": "Two generators with the same seed produce the same sequence. That's what makes generated test data reproducible." }
```

## 3. Timing a query with timeit

`timeit.repeat(fn, repeat=5, number=20)` calls `fn` 20 times per round, for 5 rounds, and returns the 5 round totals. It uses `time.perf_counter()` and switches off garbage collection while timing, so rounds are comparable.

**Report the minimum**, divided by `number`. The Python docs explain why: the lowest value is what your machine can actually do; higher values are usually other processes interfering, not your code. A mean would mix that noise in.

```python
sql = "SELECT id, body FROM messages WHERE chat_id = ? ORDER BY created_at DESC LIMIT 50"

def run():
    conn.execute(sql, (7,)).fetchall()

def best(fn, number=20):
    return min(timeit.repeat(fn, repeat=5, number=number)) / number

before = best(run)
conn.execute("CREATE INDEX idx_messages_chat_created ON messages (chat_id, created_at)")
after = best(run)
print(f"no index:   {before * 1e6:9.1f} µs per query")
print(f"with index: {after * 1e6:9.1f} µs per query")
print(f"speed-up:   {before / after:9.0f}x")
```

On this machine (two runs):

```console
no index:      2671.8 µs per query
with index:      14.2 µs per query
speed-up:         189x
no index:      2640.4 µs per query
with index:      14.1 µs per query
speed-up:         187x
```

Your numbers will differ; the **ratio** and the plans are what you compare. Note `.fetchall()` inside `run`: `execute()` alone only starts a query, so without fetching you'd time almost nothing.

```quiz
{ "id": "q3", "type": "output",
  "prompt": "A query was timed with `timeit.repeat(run, repeat=3, number=20)`, which returned `[0.84, 0.62, 0.71]` (seconds per round). What does this print?",
  "code": "rounds = [0.84, 0.62, 0.71]\nprint(f'{min(rounds) / 20 * 1000:.1f} ms per query')",
  "answer": "31.0 ms per query",
  "explanation": "The fastest round, 0.62 s, covered 20 calls, so one call took 0.031 s, which is 31.0 ms." }
```

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "Why report the minimum of the rounds rather than the mean?",
  "options": ["Slower rounds are mostly other processes interfering, so the minimum is the best estimate of the code's own cost", "The minimum is always the round that ran the most iterations", "The mean can't be computed for floats", "timeit only stores the minimum"], "answer": 0,
  "explanation": "That's the reasoning in the timeit docs: higher values are usually caused by interference, not by variability in the code itself." }
```

## 4. What indexes cost on writes

Every index is a sorted structure the database must update on each insert. Measured here: 50,000 inserts into a fresh table with 0 to 3 extra indexes (fixed data, `min` of 3 rounds):

```python
INDEXES = [
    "CREATE INDEX idx_chat_created ON messages (chat_id, created_at)",
    "CREATE INDEX idx_sender ON messages (sender_id)",
    "CREATE INDEX idx_body ON messages (body)",
]

def fresh_table(n_indexes):
    conn.execute("DROP TABLE IF EXISTS messages")
    conn.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, chat_id INTEGER, "
                 "sender_id INTEGER, body TEXT, created_at TEXT)")
    for ddl in INDEXES[:n_indexes]:
        conn.execute(ddl)

def load():
    with conn:
        conn.executemany("INSERT INTO messages (chat_id, sender_id, body, created_at) "
                         "VALUES (?, ?, ?, ?)", rows)

for n in range(len(INDEXES) + 1):
    t = min(timeit.repeat(load, setup=lambda: fresh_table(n), repeat=3, number=1))
    print(f"{n} extra index(es): {t * 1000:4.0f} ms for 50,000 inserts")
```

On this machine:

```console
0 extra index(es):   15 ms for 50,000 inserts
1 extra index(es):   34 ms for 50,000 inserts
2 extra index(es):   50 ms for 50,000 inserts
3 extra index(es):   71 ms for 50,000 inserts
```

Each index roughly added the cost of another table's worth of writes; three indexes made loading almost **5 times slower**. (The `setup` callable rebuilds the table before each round and isn't included in the timing.) For a messenger, where inserting messages is *the* hot write path, that's a real price. Pay it for indexes that serve hot reads, not "just in case".

```quiz
{ "id": "q5", "type": "choice", "label": "Application",
  "prompt": "Using the numbers above: a service inserts 2,000 messages per second at peak. Someone proposes an index on `body` 'in case we add search later'. What's the best response?",
  "options": ["Don't add it now: it slows every insert on the hottest write path and serves no query yet; add it with the feature, measured", "Add it: indexes only affect reads", "Add it, since 3 indexes are the recommended maximum", "Add it and drop the primary key to compensate"], "answer": 0,
  "explanation": "An index with no query to serve is pure write cost. When search arrives, measure the real query (and a plain index on body may not even help LIKE '%word%')." }
```

## 5. When an index makes a query slower

`is_deleted` is 0 or 1, about half the rows each. Here is the same query with and without an index on it (200,000 rows, `min` of 5 rounds, two runs):

```console
index=False   15.9 ms  ['SCAN messages']
index=True    19.0 ms  ['SEARCH messages USING INDEX idx_messages_deleted (is_deleted=?)']
index=False   16.2 ms  ['SCAN messages']
index=True    19.5 ms  ['SEARCH messages USING INDEX idx_messages_deleted (is_deleted=?)']
```

The plan looks "better" (SEARCH) but it's about 20% **slower**: for each of 100,000 matches SQLite reads the index entry and then looks the row up in the table, instead of reading the table once in order. An index pays off when it narrows the result to a **small fraction** of the table (its *selectivity*). One chat out of 1,000 is selective; "not deleted" is not.

Running `ANALYZE` (which stores row-count statistics in `sqlite_stat1` for the planner) didn't change this plan here. The planner works from estimates. Your measurement is the evidence.

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "Write the 3–4 lines you'd put in a pull request that adds `CREATE INDEX idx_messages_chat_created ON messages (chat_id, created_at)`, to justify it.",
  "model": "Query: chat history page (WHERE chat_id = ? ORDER BY created_at DESC LIMIT 50). Before: SCAN messages + USE TEMP B-TREE, ~2.7 ms per query on 200k generated rows. After: SEARCH USING INDEX (chat_id=?), no sort, ~14 µs (about 190x). Write cost: about +19 ms per 50k inserts on the same machine; the history page is read far more often than messages are written, so it's worth it. No existing index is a prefix of it.",
  "explanation": "A justified index names the query, shows plan and timing before and after on realistic data, and accounts for the write cost." }
```

## 6. Your turn

Turn this lesson's scripts into three reusable helpers: `best_time` (the min-per-call rule), `seed_messages` (reproducible data in one transaction) and `index_report` (plan and time, before and after). The tests check the edge cases too: zero rounds, zero rows and the same seed twice.

```exercise
DB.M05.L03.E1
```
