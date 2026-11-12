```python
def best_time(fn, number=10, repeat=5):
    if number < 1 or repeat < 1:
        raise ValueError("number and repeat must be >= 1")
    rounds = timeit.repeat(fn, number=number, repeat=repeat)
    return min(rounds) / number


def seed_messages(conn, n, chats, seed=0):
    rng = random.Random(seed)
    rows = [(rng.randint(1, chats), rng.randint(1, 1000), f"generated message {i}",
             f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}") for i in range(n)]
    with conn:
        conn.executemany("INSERT INTO messages (chat_id, sender_id, body, created_at) VALUES (?, ?, ?, ?)", rows)
    return n


def index_report(conn, sql, params, index_ddl, number=20):
    def run_query():
        conn.execute(sql, params).fetchall()

    report = {"plan_before": _plan(conn, sql, params), "before": best_time(run_query, number=number)}
    conn.execute(index_ddl)
    report["plan_after"] = _plan(conn, sql, params)
    report["after"] = best_time(run_query, number=number)
    return report
```

**Why it works**

- `timeit.repeat` returns one total per round. The Python docs recommend the **minimum**: slower rounds are usually
  other processes interfering, not your code. Dividing by `number` gives seconds per call, so numbers from different
  `number` settings are comparable.
- `random.Random(seed)` is a private generator: the same seed gives the same rows on every run and machine, and it
  doesn't disturb the global `random` state other code may use. Reproducible data makes before/after comparisons fair.
- `with conn:` commits all inserts as **one** transaction (DB.M03). Committing per row is far slower and would make
  your seeding dominate the measurement.
- `.fetchall()` inside the timed function matters: `execute()` alone only starts the query. Without fetching you
  time almost nothing.
- The plan is captured next to each timing, so the report explains *why* the number changed.

**Edge cases:** `n=0` builds an empty list, and `executemany` with no rows is fine. Zero rounds would divide by
zero or call `min([])`, so they're rejected up front with a clear `ValueError`.

**Limitation:** the test only asserts `after < before` on 30,000 rows, where the gap is large. On tiny tables,
timing noise can be bigger than the difference, which is exactly why you measure at realistic volume.
