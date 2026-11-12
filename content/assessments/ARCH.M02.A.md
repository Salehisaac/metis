---
{ "id": "ARCH.M02.A", "module": "ARCH.M02", "title": "ARCH.M02 module assessment: caching with Redis", "minutes": 20 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. The explain questions are discussed with the mentor: they're the evidence for "reason about stale reads".

```quiz
{ "id": "a1", "type": "output",
  "prompt": "What does this print?",
  "code": "import fakeredis\n\nr = fakeredis.FakeRedis(decode_responses=True)\nr.set(\"cache:p:1\", \"{}\", ex=60)\nr.set(\"cache:p:1\", \"{\\\"v\\\": 2}\")\nprint(r.ttl(\"cache:p:1\"), r.ttl(\"cache:p:2\"))",
  "answer": "-1 -2",
  "explanation": "The second SET has no ex, so it discards the TTL: the entry is now immortal (-1). cache:p:2 doesn't exist (-2)." }
```

```quiz
{ "id": "a2", "type": "choice",
  "prompt": "Which write path is correct for a cache-aside entry `cache:order:{id}`?",
  "options": ["DEL the key, then UPDATE and COMMIT", "UPDATE, COMMIT, then SET the key to the new value", "UPDATE, COMMIT, then DEL the key", "UPDATE, DEL the key, then COMMIT"], "answer": 2,
  "explanation": "Delete (order-free, unlike SET) and do it after the commit, so a concurrent reader can't re-cache the old committed value with a fresh TTL." }
```

```quiz
{ "id": "a3", "type": "truefalse",
  "prompt": "With 'commit, then delete', a reader can never end up caching a stale value.", "answer": false,
  "explanation": "A reader that missed and read the old row before the commit, then wrote the cache after the delete, leaves a stale entry. It's rare, and the TTL bounds it." }
```

```quiz
{ "id": "a4", "type": "output",
  "prompt": "What does this print?",
  "code": "import json\nimport fakeredis\n\nr = fakeredis.FakeRedis(decode_responses=True)\nloads = []\n\ndef load(i):\n    loads.append(i)\n    return None\n\ndef get(i):\n    raw = r.get(f\"cache:item:{i}\")\n    if raw is not None:\n        return json.loads(raw)\n    item = load(i)\n    r.set(f\"cache:item:{i}\", json.dumps(item), ex=30 if item is None else 600)\n    return item\n\nfor i in [5, 5, 6, 5]:\n    get(i)\nprint(loads, r.ttl(\"cache:item:5\"))",
  "answer": "[5, 6] 30",
  "explanation": "Missing items are cached as JSON null with the short negative TTL, so the repeated 5s are answered by the cache. Only the first lookup of each id reaches the loader." }
```

```quiz
{ "id": "a5", "type": "explain", "label": "Design review",
  "prompt": "Users report that after changing their display name, the old name sometimes shows for about 5 minutes, then fixes itself. The code commits, then deletes `cache:user:{id}`. The TTL is 300 s. List the possible causes you'd check, in order.",
  "model": "(1) Another cached shape still contains the name (team member lists, comment authors) and isn't invalidated, so it lives out its TTL. (2) The delete failed (Redis error swallowed somewhere) and the entry expired after 300 s. (3) The remaining race: a reader read the old row before the commit and filled the cache after the delete. (4) The commit actually happens later than the delete, for example in a dependency after yield. 'About 5 minutes' matches the TTL, so the stale copy was being served until expiry; check logs for invalidation failures and list every key containing the name.",
  "explanation": "A staleness window equal to the TTL means an invalidation was missed, failed or raced; find which." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Design review",
  "prompt": "A teammate wants to protect a `withdraw` operation with the cache stampede lock (`SET lock:account:{id} token NX PX 2000`) instead of a database transaction, 'because Redis is faster'. What do you say?",
  "model": "No. That lock is fine for stampede protection, where two holders only cost an extra query, but not for correctness: it expires after 2 s even if the holder is still working (a GC pause or a slow query), after which two withdrawals can run at once. It also doesn't make the database writes atomic: a crash between steps leaves partial state. The Redis docs themselves discourage the simple SET NX pattern for real locking. Keep the conditional UPDATE plus transaction in the database, which is the source of truth.",
  "explanation": "Cache locks are an optimisation; invariants on money belong to the database." }
```
