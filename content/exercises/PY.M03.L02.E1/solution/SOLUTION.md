```python
from collections import Counter


def _unique_lower(tags: list[str]) -> list[str]:
    seen = set()
    result = []
    for tag in tags:
        low = tag.lower()
        if low not in seen:
            seen.add(low)
            result.append(low)
    return result


def count_tags(posts):
    total = Counter()
    for tags in posts.values():
        for tag in _unique_lower(tags):
            total[tag] += 1
    return dict(total)


def posts_by_tag(posts):
    index = {}
    for post_id, tags in posts.items():
        for tag in _unique_lower(tags):
            index.setdefault(tag, []).append(post_id)
    return index


def shared_tags(posts, a, b):
    first = set(_unique_lower(posts.get(a, [])))
    second = set(_unique_lower(posts.get(b, [])))
    return sorted(first & second)
```

**Why it works**

- **One helper does the normalisation.** `_unique_lower` is the "seen set plus result list" pattern from section 5: it de-duplicates case-insensitively *and* keeps the original order. Every function relies on it, so the rule "case-insensitive, once per post" is written once.
- **Counting:** `Counter` returns 0 for a missing tag, so `total[tag] += 1` needs no `get`. Because each post's tags are already unique, `['Go', 'web', 'WEB']` adds 1 to `web`, not 2.
- **Grouping:** `setdefault(tag, [])` gives back the existing list or a new empty one. Ids come out in the posts' order because the dict preserves insertion order and the outer loop follows it, and new tags are added in first-seen order.
- **Comparing:** `&` is set intersection. A set has no order, so `sorted(...)` turns it into the alphabetical list the spec asks for. `posts.get(a, [])` makes an unknown id behave like an empty post, with no KeyError.
- **No mutation:** `tag.lower()` returns a new string, and the helper builds new lists, so the caller's dict is untouched.

**Alternatives**

- `defaultdict(int)` or `counts.get(tag, 0) + 1` instead of `Counter`: same result. `defaultdict(list)` instead of `setdefault`, returned as `dict(index)`.
- After L05 you could write `{tag.lower() for tag in posts.get(a, [])}` for the sets in `shared_tags`.
