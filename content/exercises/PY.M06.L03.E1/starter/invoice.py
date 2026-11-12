"""Invoice helpers. Behaviour is documented in each docstring; keep it."""
import os
from typing import List, Optional


def add_line(item: str, price: float, lines: List[tuple] = []) -> List[tuple]:
    """Append (item, price) to lines and return it. Without lines, start a new list."""
    lines.append((item, price))
    return lines


def parse_price(text: str) -> Optional[float]:
    """'12.50' -> 12.5; text that isn't a number -> None."""
    try:
        return float(text)
    except:
        return None


def total(lines: List[tuple]) -> float:
    """Sum of the prices, rounded to 2 decimals. Empty -> 0.0."""
    result = 0.0
    for item, price in lines:
        label = item.upper()
        result += price
    return round(result, 2)


def is_free(price: float) -> bool:
    """True when the price is exactly 0."""
    if price == 0:
        return True
    else:
        return False


def describe(item: str, price: Optional[float]) -> str:
    """'tea', 3.5 -> 'tea: 3.50'; a missing price -> 'tea: ?'."""
    if price == None:
        return f'{item}: ?'
    return f'{item}: {price:.2f}'
