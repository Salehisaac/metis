import sys


def count_words(text: str) -> int:
    """Number of whitespace-separated words in text."""
    return len(text.split())


text = " ".join(sys.argv[1:])
print(count_words(text))
