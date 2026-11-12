def initials(full_name: str) -> str:
    """'ada lovelace' -> 'AL'. Extra spaces are ignored; '' -> ''."""
    result = ""
    for part in full_name.split(" "):
        result += part[0]
    return result
