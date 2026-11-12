```python
def top_senders(messages: list[tuple[str, str]], n: int) -> list[str]:
    if n < 0:
        raise ValueError("n must be >= 0")
    counts = {}
    for sender, text in messages:
        if text:
            counts[sender] = counts.get(sender, 0) + 1
    ranked = sorted(counts, key=lambda name: (-counts[name], name))
    return ranked[:n]
```

**Why it works**

- **Count:** the `get(sender, 0) + 1` idiom from L02. `if text:` is false for `""`, so empty messages are skipped. A sender whose messages are all empty never becomes a key, so they can't appear in the result.
- **Rank:** `sorted(counts)` sorts the dict's keys (the names). The key `(-counts[name], name)` compares the negated counts first, so more messages means a smaller key and an earlier position. Only on equal counts does it compare names, A to Z. With kian 2, tara 1, dana 1, the keys are `(-2, 'kian')`, `(-1, 'dana')` and `(-1, 'tara')`, so the ranking is kian, dana, tara.
- **Cut:** `ranked[:n]` returns the first n. It returns all of them when n is larger (slices clamp), and `[]` when n is 0.
- **No mutation:** `sorted` builds a new list; the input list is only read.

**What went wrong in the Go attempt, and what prevents it here**

- `n` was read as "senders with exactly n messages". The test `test_n_is_a_ranking_size_not_a_count` pins the meaning down.
- There was no sort, so the order came from Go's random map iteration. Here the order comes from one explicit key, and Python's dict order (insertion order) is never relied on.
- Only the given example was tested. The tests here add ties, the cutoff, a large n, n == 0 and empty text.

**Alternatives**

- `Counter(sender for sender, text in messages if text)` for the counting step (a generator expression, L05), followed by the same `sorted` call. Don't use `most_common(n)` for the ranking: its ties follow first appearance.
- Two stable passes, `sorted(sorted(counts), key=counts.get, reverse=True)`, give the same result: first sort names A to Z, then sort by count descending; stability keeps equal counts in A to Z order.
- With very many senders and a small n, `heapq.nsmallest(n, counts, key=...)` avoids sorting everything. You won't need that at this size.
