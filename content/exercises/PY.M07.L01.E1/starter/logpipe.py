"""A lazy log-processing pipeline: three generator functions you can chain."""


def parse_lines(lines):
    """Yield (LEVEL, message) for each meaningful line.

    "  warn  disk 91%  " -> ("WARN", "disk 91%"); "DEBUG" -> ("DEBUG", "").
    Blank lines and lines starting with "#" are skipped.
    """
    raise NotImplementedError


def only_level(records, level):
    """Yield the (LEVEL, message) records whose level equals `level` (case-insensitive)."""
    raise NotImplementedError


def first_n(items, n):
    """Yield at most n items, and never pull more than n items from `items`."""
    raise NotImplementedError
