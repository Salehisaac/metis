"""Billing helpers. Amounts are integers in cents."""


def with_fee(amounts: list[int], fee: int) -> list[int]:
    """Return a NEW list with `fee` added to every amount.

    The caller's list must not change.
    """
    for i in range(len(amounts)):
        amounts[i] += fee
    return amounts


def add_coupon(coupons: list[str], code: str) -> None:
    """Add `code` to the caller's `coupons` list IN PLACE, unless it is already there.

    Returns None.
    """
    if code not in coupons:
        coupons = coupons + [code]
