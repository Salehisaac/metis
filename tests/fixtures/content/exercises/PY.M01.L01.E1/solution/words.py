def count_words(text: str) -> dict[str, int]:
    """Return how often each word appears (case-insensitive)."""
    counts: dict[str, int] = {}
    for word in text.lower().split():
        counts[word] = counts.get(word, 0) + 1
    return counts
