from billing import add_coupon, with_fee


def test_with_fee_result():
    assert with_fee([100, 250], 30) == [130, 280]


def test_with_fee_leaves_input_unchanged():
    prices = [100, 250]
    with_fee(prices, 30)
    assert prices == [100, 250]


def test_with_fee_returns_a_new_list():
    prices = [100]
    assert with_fee(prices, 5) is not prices


def test_with_fee_twice_does_not_double_charge():
    prices = [100]
    with_fee(prices, 10)
    assert with_fee(prices, 10) == [110]


def test_with_fee_empty():
    assert with_fee([], 30) == []


def test_add_coupon_changes_callers_list():
    coupons = ["WELCOME"]
    add_coupon(coupons, "BLACKFRIDAY")
    assert coupons == ["WELCOME", "BLACKFRIDAY"]


def test_add_coupon_to_empty_list():
    coupons = []
    add_coupon(coupons, "WELCOME")
    assert coupons == ["WELCOME"]


def test_add_coupon_skips_duplicates():
    coupons = ["WELCOME"]
    add_coupon(coupons, "WELCOME")
    assert coupons == ["WELCOME"]


def test_add_coupon_returns_none():
    assert add_coupon([], "X") is None
