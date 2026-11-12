```python
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
```

**Why it works**

- **Importing is silent.** The top level now only defines things. All the work is inside `main`, and `main` runs only under the guard.
- **`main` takes `argv` as a parameter instead of reading `sys.argv` itself.** Tests can pass any argument list, the way you'd inject dependencies in Go instead of reading globals.
- **Exit codes come from one place:** `sys.exit(main(sys.argv))`. A return of 2 means a usage error (the Unix convention). Usage text goes to stderr, so `python3 wordcount.py | other-tool` never receives it as data.

**Alternative:** `argparse` from the standard library generates usage and help messages for you. It's worth using once a tool has options. For this exercise, it would hide the mechanics you're practising.
