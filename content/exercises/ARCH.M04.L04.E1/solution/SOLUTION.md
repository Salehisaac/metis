# Reference solution

One possible doc (there are other good ones). The structural tests are the easy part; the review below is the real check.

````markdown
# Design: Short links with click counts

<!-- The brief is in BRIEF.md. Replace every TODO. Keep the whole doc under 1200 words. -->

## Context and scope

Marketing needs short links (`go.example.com/abc123` or a custom alias) that redirect to campaign URLs, with daily
click counts per link. This doc covers link creation, redirects, expiry and daily counts. Analytics beyond daily
counts (geography, devices, unique visitors) are out of scope.

## Goals

- Redirect p99 under 50 ms at the server, at about 930 rps peak.
- A short code or alias maps to exactly one link; aliases are unique.
- Daily click counts per link, at most 5 minutes behind; a click is never counted twice for a day by a retry of the counter job.
- Expired links stop redirecting within 1 minute of their expiry time.

## Non-goals

- Unique-visitor counts, geography or device breakdowns.
- Editing a link's target after creation (create a new link instead).
- Public sign-up: only the marketing team creates links.

## Estimates

- Clicks: 200,000 links x 50 = 10,000,000 per day, so about 116 rps average and about 926 rps at the 8x peak.
- Creates: 200,000 per day, about 3 rps average, about 19 rps peak.
- Storage: 200,000 links x 365 x 2 years = 146 million links; at about 300 bytes each, about 44 GB.
  Daily counts: one row per link per active day; assume 10 active days, so 1.46 billion rows x 30 bytes = about 44 GB.
- Decisions: reads dominate writes about 50:1, and redirects need low latency, so redirects read through a cache.
  Clicks are counted asynchronously in batches; writing one counter row per click (926 writes per second) is avoidable.

## Data model

```sql
CREATE TABLE links (
    code TEXT PRIMARY KEY,              -- 7 random base62 characters, or the custom alias
    target_url TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER                  -- NULL = never
);
CREATE TABLE daily_clicks (
    code TEXT NOT NULL REFERENCES links(code),
    day TEXT NOT NULL,                  -- 'YYYY-MM-DD' in UTC
    clicks INTEGER NOT NULL,
    PRIMARY KEY (code, day)
);
```

The primary key on `code` makes aliases unique: creating an existing alias fails with a constraint error, which
becomes 409. Random codes have 62^7 (about 3.5 trillion) possibilities, so a collision is retried once.

## API

- `POST /links` with `{"target_url", "alias"?, "expires_at"?}`: 201 with the code; 409 alias taken; 422 bad URL.
  Requires a staff login.
- `GET /{code}`: 302 redirect to the target; 404 unknown; 410 expired. 302, not 301, because a 301 is a permanent
  redirect that browsers may cache: an expired link could keep redirecting from the browser cache, and we'd miss
  those clicks.
- `GET /links/{code}/clicks?from=2026-11-01&to=2026-11-30`: 200 with daily counts. Staff only.

## Alternatives considered

- Counting clicks with a database UPDATE per redirect: rejected because 926 writes per second on hot rows adds
  latency to the redirect path and contends on popular links. Chosen: each redirect does Redis INCR on
  `clicks:{code}:{day}`; a worker flushes the counters to `daily_clicks` every minute.
- Sequential ids encoded in base62: rejected because codes become guessable and reveal volume. Chosen: random codes.
- No cache for redirects: rejected because the 50 ms p99 at about 930 rps is safer with cache-aside (TTL 5 minutes,
  invalidated on expiry and deletion) in front of the primary-key lookup.

## Failure modes

| Failure | User sees | Detection | Mitigation |
|---|---|---|---|
| Redis down | Redirects slower; clicks during the outage not counted | Degraded-redirect metric, Redis alert | Fall back to the database for redirects; accept lost counts (counts are not billing data) |
| Database down | New links fail; cached redirects still work, others 503 | Error rate alert | Managed database with failover; redirects keep serving from cache until TTL |
| Counter flush worker down | Counts stop updating | Alert when the oldest unflushed counter is over 5 minutes old | Restart; counters wait in Redis (TTL 2 days) |
| Flush crashes after writing the DB but before deleting counters | Double counting for that minute | Reconciliation check | Flush with an absolute value per (code, day) instead of adding, so a repeat is idempotent |

## Cross-cutting concerns

- Security: only authenticated staff create links; target URLs must be http(s) and are checked against a deny list to stop the shortener being used for phishing.
- Privacy: no IP addresses or user agents are stored, only daily counts.
- Observability: redirect latency p99, cache hit rate, 404/410 rates, counter flush lag.
````

**Why this doc works (what the mentor review looks for)**

- **The numbers drive the design.** 10 million clicks a day against 200,000 creates (50:1) says the system is about redirects and counting. The ~926 rps peak justifies a cache on the redirect path and rules out one database write per click. Compare L01's booking example, where 12 rps justified *no* cache.
- **The invariant is enforced by the database.** "One code, one link" is the primary key on `code`. Alias collisions become a constraint error mapped to 409, not a check-then-insert race (ARCH.M01.L02, ARCH.M04.L02).
- **Every alternative names its reason.** Per-click UPDATE is rejected because of the latency goal and hot-row contention, sequential ids because of guessability, no-cache because of the p99 goal.
- **The redirect status is a decision, not a default.** A permanent redirect can be cached by browsers, which would break expiry and hide clicks; 302 keeps every click visible to the server.
- **Failure modes come with detection** and an honest user impact. "Clicks during a Redis outage are lost" is acceptable *because* the counts are marketing data, not billing; the doc says so. The last row reuses ARCH.M03's idempotency idea: flushing absolute values makes a repeated flush harmless.

**Common gaps in first drafts:** goals like "fast and scalable" with no numbers; a schema with no uniqueness rule for aliases; counting clicks with `UPDATE ... SET clicks = clicks + 1` in the redirect request; no mention of what happens to cached redirects when a link expires; failure modes without detection; 301 chosen without thinking about browser caching.
