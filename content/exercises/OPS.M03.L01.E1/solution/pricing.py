DISCOUNTS = {"WELCOME": 10, "VIP": 25}


def discount_for(code: str | None) -> int:
    """Percent discount for a code; unknown codes give 0. A non-string code is a caller bug."""
    try:
        return DISCOUNTS[code.upper()]
    except KeyError:
        return 0


def basket_total(prices: list[int], codes: list[str] | None = None) -> int:
    """Total in cents after the best discount among codes (the codes list is not modified)."""
    all_codes = [*(codes or []), "NONE"]
    best = max(discount_for(c) for c in all_codes)
    subtotal = sum(prices)
    return subtotal - subtotal * best // 100
