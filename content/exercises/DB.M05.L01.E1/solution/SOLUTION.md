```python
def explain(conn, sql, params=()):
    plan_rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}", params).fetchall()
    return [detail for _node, _parent, _unused, detail in plan_rows]


def full_scans(conn, sql, params=()):
    scanned = []
    for detail in explain(conn, sql, params):
        words = detail.split()
        if words[0] == "SCAN" and detail != "SCAN CONSTANT ROW":
            scanned.append(words[1])
    return scanned
```

**Why it works**

- Prefixing a statement with `EXPLAIN QUERY PLAN` makes SQLite *plan* it and return the plan as rows instead of
  running it. That's why explaining a `DELETE` deletes nothing. The parameters still go through `?` placeholders:
  the planner works on the same statement your app will run, with the values bound separately.
- Each plan row has four fields (node id, parent id, an unused field, detail). Only the fourth is the human-readable
  part, so unpacking the tuple names what you're throwing away.
- A full scan is a detail that starts with the word `SCAN`. The second word is the table name *as written in the
  query*, so an alias (`m`, `c`) stays an alias. `SCAN CONSTANT ROW` is SQLite's way of saying "no table at all".
- `full_scans` reuses `explain`, so there's one place that talks to SQLite.

**Edge cases the tests pinned down**

- No params: `params=()` is a valid empty tuple for `execute`.
- The plan changes the moment an index exists, so never cache a plan across schema changes.
- `SCAN m USING COVERING INDEX ...` still counts: it walks the whole index, which is cheaper than the table but still
  proportional to the row count.

**Limitation:** the SQLite docs warn the EXPLAIN QUERY PLAN text may change between releases. Use helpers like this
in tests and debugging scripts, not in production logic.
