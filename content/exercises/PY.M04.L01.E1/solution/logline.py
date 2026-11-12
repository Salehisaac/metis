def log_line(level, *words, ts=None, **fields):
    """Build one structured log line. See exercise.json for the rules."""
    parts = [level.upper(), *words]
    if ts is not None:
        parts.insert(0, ts)
    for key in sorted(fields):
        value = str(fields[key])
        if " " in value:
            value = f'"{value}"'
        parts.append(f"{key}={value}")
    return " ".join(parts)
