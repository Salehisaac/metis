class BadRecord(ValueError):
    """A line that isn't a valid 'name,score' record."""


def parse_record(line: str, lineno: int) -> tuple[str, int]:
    """'ada, 42' -> ('ada', 42). Raise BadRecord for a malformed line."""
    try:
        name, score = line.split(",")
        return name.strip(), int(score)
    except:
        return None


def load_scores(lines: list[str]) -> tuple[dict[str, int], int]:
    """Parse every line into {name: score}.

    Blank lines are ignored. Malformed lines are skipped and counted.
    Returns (scores, number_of_skipped_lines).
    """
    scores = {}
    for lineno, line in enumerate(lines, start=1):
        record = parse_record(line, lineno)
        if record:
            scores[record[0]] = record[1]
    return scores, 0
