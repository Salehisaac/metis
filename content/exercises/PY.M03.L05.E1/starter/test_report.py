from report import cents_by_id, customers_with, has_order_over, paid_ids, revenue

ORDERS = [
    {"id": 7, "customer": "mina", "cents": 1250, "status": "paid"},
    {"id": 3, "customer": "omid", "cents": 400, "status": "pending"},
    {"id": 9, "customer": "mina", "cents": 900, "status": "paid"},
    {"id": 4, "customer": "ali", "cents": 5000, "status": "refunded"},
    {"id": 5, "customer": "ali", "cents": 300, "status": "paid"},
]


def test_paid_ids_in_input_order():
    assert paid_ids(ORDERS) == [7, 9, 5]


def test_cents_by_id():
    assert cents_by_id(ORDERS) == {7: 1250, 3: 400, 9: 900, 4: 5000, 5: 300}


def test_customers_with_status_distinct_and_sorted():
    assert customers_with(ORDERS, "paid") == ["ali", "mina"]
    assert customers_with(ORDERS, "refunded") == ["ali"]


def test_customers_with_unknown_status():
    assert customers_with(ORDERS, "shipped") == []


def test_revenue_counts_only_paid():
    assert revenue(ORDERS) == 1250 + 900 + 300


def test_has_order_over_is_strict():
    assert has_order_over(ORDERS, 4999) is True
    assert has_order_over(ORDERS, 5000) is False


def test_empty_orders():
    assert paid_ids([]) == []
    assert cents_by_id([]) == {}
    assert customers_with([], "paid") == []
    assert revenue([]) == 0
    assert has_order_over([], 0) is False


def test_input_not_modified():
    orders = [{"id": 1, "customer": "b", "cents": 10, "status": "paid"}]
    before = [dict(o) for o in orders]
    paid_ids(orders)
    cents_by_id(orders)
    customers_with(orders, "paid")
    revenue(orders)
    has_order_over(orders, 5)
    assert orders == before
