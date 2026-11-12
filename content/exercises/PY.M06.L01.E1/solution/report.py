"""Turn expense rows into a per-category report."""

from .ledger import describe, load


def totals(rows: list[tuple[str, float]]) -> list[tuple[str, float]]:
    sums: dict[str, float] = {}
    for category, amount in rows:
        sums[category] = sums.get(category, 0) + amount
    return sorted(sums.items())


def render(path: str) -> str:
    rows = load(path)
    if not rows:
        return "no expenses"
    return "\n".join(describe(category, amount) for category, amount in totals(rows))
