class BadRecord(ValueError):
    """A line that isn't a valid 'name,score' record."""


def parse_record(line: str, lineno: int) -> tuple[str, int]:
    """'ada, 42' -> ('ada', 42). Raise BadRecord for a malformed line."""
    parts = line.split(",")
    if len(parts) != 2 or not parts[0].strip():
        raise BadRecord(f"line {lineno}: expected 'name,score', got {line!r}")
    name, score = parts
    try:
        value = int(score)
    except ValueError as err:
        raise BadRecord(f"line {lineno}: bad score {score.strip()!r}") from err
    return name.strip(), value


def load_scores(lines: list[str]) -> tuple[dict[str, int], int]:
    """Parse every line into {name: score}.

    Blank lines are ignored. Malformed lines are skipped and counted.
    Returns (scores, number_of_skipped_lines).
    """
    scores = {}
    skipped = 0
    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            name, score = parse_record(line, lineno)
        except BadRecord:
            skipped += 1
        else:
            scores[name] = score
    return scores, skipped
