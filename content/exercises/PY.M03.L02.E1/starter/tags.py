# posts maps a post id to that post's tags, e.g. {1: ["Python", "web"], 2: ["go"]}.
# Tags are case-insensitive: "Python" and "python" are the same tag. Return tags in lowercase.


def count_tags(posts: dict[int, list[str]]) -> dict[str, int]:
    """How many posts use each tag. A tag repeated within one post counts once for that post."""
    raise NotImplementedError


def posts_by_tag(posts: dict[int, list[str]]) -> dict[str, list[int]]:
    """Map each tag to the ids of the posts that use it, in the order the posts appear, each id once."""
    raise NotImplementedError


def shared_tags(posts: dict[int, list[str]], a: int, b: int) -> list[str]:
    """Tags used by both post a and post b, sorted alphabetically. An unknown post id has no tags."""
    raise NotImplementedError
