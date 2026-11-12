"""A lazy log-processing pipeline: three generator functions you can chain."""


def parse_lines(lines):
    """Yield (LEVEL, message) for each meaningful line.

    "  warn  disk 91%  " -> ("WARN", "disk 91%"); "DEBUG" -> ("DEBUG", "").
    Blank lines and lines starting with "#" are skipped.
    """
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        message = parts[1] if len(parts) == 2 else ""
        yield parts[0].upper(), message


def only_level(records, level):
    """Yield the (LEVEL, message) records whose level equals `level` (case-insensitive)."""
    wanted = level.upper()
    for record in records:
        if record[0] == wanted:
            yield record


def first_n(items, n):
    """Yield at most n items, and never pull more than n items from `items`."""
    if n <= 0:
        return
    count = 0
    for item in items:
        yield item
        count += 1
        if count == n:
            return
