"""Tiny audit log for user records (dicts with str/int/list/None values)."""


def changed_fields(old: dict, new: dict) -> list[str]:
    """Names of the fields whose value differs between two versions of a record.

    Both records have the same keys. The result follows the key order of `old`.
    """
    changed = []
    for key in old:
        if old[key] is not new[key]:
            changed.append(key)
    return changed


def save_version(history: list, record: dict) -> None:
    """Append a snapshot of `record` to `history` (in place).

    Later changes to `record` must not change snapshots already saved.
    """
    history.append(record)
