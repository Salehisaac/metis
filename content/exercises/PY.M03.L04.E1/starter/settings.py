def parse_settings(text: str) -> dict[str, str]:
    """Parse lines of `key = value` into a dict.

    - Spaces around keys and values are removed.
    - Blank or whitespace-only lines are skipped.
    - Lines whose first non-space character is '#' are comments and are skipped.
    - Only the first '=' separates key and value; the value may contain more '='.
    - An empty value is allowed. A later line overrides an earlier one with the same key.
    - A line with no '=', or with an empty key, raises ValueError naming the line number (1-based).
    """
    raise NotImplementedError


def parse_list(value: str) -> list[str]:
    """Split a comma-separated value into items, trimming spaces and dropping empty items."""
    raise NotImplementedError
