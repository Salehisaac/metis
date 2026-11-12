"""Command-line entry point: main() returns the exit status."""

import sys

from .report import render


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m spend FILE", file=sys.stderr)
        return 2
    print(render(argv[0]))
    return 0
