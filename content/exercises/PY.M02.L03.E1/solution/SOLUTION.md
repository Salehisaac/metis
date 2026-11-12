```python
def with_fee(amounts: list[int], fee: int) -> list[int]:
    charged = []
    for amount in amounts:
        charged.append(amount + fee)
    return charged


def add_coupon(coupons: list[str], code: str) -> None:
    if code not in coupons:
        coupons.append(code)
```

**Bug 1: `with_fee` mutated what it should only read.** `amounts` is a second label for the caller's list, and `amounts[i] += fee` assigns into that list. Returning it doesn't make a copy, so the caller's prices were charged too, and calling it twice charged the fee twice. Building a new list (`charged`) and returning it leaves the input alone. Note that `amount + fee` makes a new int; ints can't be changed in place anyway.

**Bug 2: `add_coupon` rebound instead of mutating.** `coupons = coupons + [code]` builds a new list and moves only the function's local label to it. That new list is dropped when the function returns, so the caller saw nothing. `coupons.append(code)` changes the caller's list. `coupons += [code]` would also work (on a list, `+=` mutates in place), but `append` says what it does more clearly.

**Why the contracts differ:** `with_fee` follows the `sorted()` style (new object, input untouched); `add_coupon` follows the `list.sort()` style (mutate, return None). Each is fine; mixing them is the bug.

**Alternative for `with_fee`:** `return [amount + fee for amount in amounts]` (list comprehensions come in PY.M03).
