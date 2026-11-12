"""Invoice helpers. Behaviour is documented in each docstring; keep it."""


def add_line(item: str, price: float, lines: list[tuple] | None = None) -> list[tuple]:
    """Append (item, price) to lines and return it. Without lines, start a new list."""
    if lines is None:
        lines = []
    lines.append((item, price))
    return lines


def parse_price(text: str) -> float | None:
    """'12.50' -> 12.5; text that isn't a number -> None."""
    try:
        return float(text)
    except ValueError:
        return None


def total(lines: list[tuple]) -> float:
    """Sum of the prices, rounded to 2 decimals. Empty -> 0.0."""
    result = 0.0
    for _item, price in lines:
        result += price
    return round(result, 2)


def is_free(price: float) -> bool:
    """True when the price is exactly 0."""
    return price == 0


def describe(item: str, price: float | None) -> str:
    """'tea', 3.5 -> 'tea: 3.50'; a missing price -> 'tea: ?'."""
    if price is None:
        return f"{item}: ?"
    return f"{item}: {price:.2f}"
