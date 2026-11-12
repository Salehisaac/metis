"""Read expense lines like '2026-11-01,food,12.50'."""

from .settings import CURRENCY


def parse_line(line: str) -> tuple[str, float]:
    _date, category, amount = line.strip().split(",")
    return category.strip(), float(amount)


def load(path: str) -> list[tuple[str, float]]:
    with open(path, encoding="utf-8") as f:
        return [parse_line(line) for line in f if line.strip()]


def describe(category: str, amount: float) -> str:
    return f"{category}: {amount:.2f} {CURRENCY}"
