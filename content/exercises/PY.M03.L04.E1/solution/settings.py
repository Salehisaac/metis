def parse_settings(text: str) -> dict[str, str]:
    """Parse lines of `key = value` into a dict.

    - Spaces around keys and values are removed.
    - Blank or whitespace-only lines are skipped.
    - Lines whose first non-space character is '#' are comments and are skipped.
    - Only the first '=' separates key and value; the value may contain more '='.
    - An empty value is allowed. A later line overrides an earlier one with the same key.
    - A line with no '=', or with an empty key, raises ValueError naming the line number (1-based).
    """
    settings = {}
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"line {number}: expected 'key = value', got {stripped!r}")
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"line {number}: empty key")
        settings[key] = value.strip()
    return settings


def parse_list(value: str) -> list[str]:
    """Split a comma-separated value into items, trimming spaces and dropping empty items."""
    items = []
    for part in value.split(","):
        part = part.strip()
        if part:
            items.append(part)
    return items
