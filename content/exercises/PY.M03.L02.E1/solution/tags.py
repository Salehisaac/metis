# posts maps a post id to that post's tags, e.g. {1: ["Python", "web"], 2: ["go"]}.
# Tags are case-insensitive: "Python" and "python" are the same tag. Return tags in lowercase.
from collections import Counter


def _unique_lower(tags: list[str]) -> list[str]:
    """The post's tags in lowercase, first occurrence only, original order kept."""
    seen = set()
    result = []
    for tag in tags:
        low = tag.lower()
        if low not in seen:
            seen.add(low)
            result.append(low)
    return result


def count_tags(posts: dict[int, list[str]]) -> dict[str, int]:
    """How many posts use each tag. A tag repeated within one post counts once for that post."""
    total = Counter()
    for tags in posts.values():
        for tag in _unique_lower(tags):
            total[tag] += 1
    return dict(total)


def posts_by_tag(posts: dict[int, list[str]]) -> dict[str, list[int]]:
    """Map each tag to the ids of the posts that use it, in the order the posts appear, each id once."""
    index = {}
    for post_id, tags in posts.items():
        for tag in _unique_lower(tags):
            index.setdefault(tag, []).append(post_id)
    return index


def shared_tags(posts: dict[int, list[str]], a: int, b: int) -> list[str]:
    """Tags used by both post a and post b, sorted alphabetically. An unknown post id has no tags."""
    first = set(_unique_lower(posts.get(a, [])))
    second = set(_unique_lower(posts.get(b, [])))
    return sorted(first & second)
