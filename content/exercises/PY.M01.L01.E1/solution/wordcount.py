import sys


def count_words(text: str) -> int:
    """Number of whitespace-separated words in text."""
    return len(text.split())


def main(argv: list[str]) -> int:
    words = argv[1:]
    if not words:
        print("usage: python3 wordcount.py WORDS...", file=sys.stderr)
        return 2
    print(count_words(" ".join(words)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
