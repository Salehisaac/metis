import pytest

from paging import last, page

EVENTS = ["e1", "e2", "e3", "e4", "e5", "e6", "e7"]


def test_first_page():
    assert page(EVENTS, 1, 3) == ["e1", "e2", "e3"]


def test_middle_page():
    assert page(EVENTS, 2, 3) == ["e4", "e5", "e6"]


def test_last_partial_page():
    assert page(EVENTS, 3, 3) == ["e7"]


def test_page_past_the_end_is_empty():
    assert page(EVENTS, 4, 3) == []
    assert page(EVENTS, 100, 3) == []


def test_page_of_empty_list():
    assert page([], 1, 10) == []


def test_page_bigger_than_list():
    assert page(EVENTS, 1, 50) == EVENTS


def test_page_rejects_bad_number_and_size():
    with pytest.raises(ValueError):
        page(EVENTS, 0, 3)
    with pytest.raises(ValueError):
        page(EVENTS, -1, 3)
    with pytest.raises(ValueError):
        page(EVENTS, 1, 0)


def test_page_returns_a_new_list():
    items = ["a", "b"]
    result = page(items, 1, 2)
    result.append("c")
    assert items == ["a", "b"]


def test_last_n():
    assert last(EVENTS, 2) == ["e6", "e7"]


def test_last_more_than_available():
    assert last(EVENTS, 10) == EVENTS


def test_last_zero_is_empty():
    assert last(EVENTS, 0) == []


def test_last_rejects_negative():
    with pytest.raises(ValueError):
        last(EVENTS, -1)
