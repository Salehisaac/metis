from cachekey import cache_key


def test_single_param():
    assert cache_key({"q": "fastapi"}) == (("q", "fastapi"),)


def test_pairs_are_sorted_by_name():
    assert cache_key({"q": "go", "page": 2}) == (("page", 2), ("q", "go"))


def test_insertion_order_does_not_matter():
    assert cache_key({"a": 1, "b": 2}) == cache_key({"b": 2, "a": 1})


def test_list_values_become_tuples():
    assert cache_key({"tags": ["go", "py"], "page": 1}) == (("page", 1), ("tags", ("go", "py")))


def test_empty_params():
    assert cache_key({}) == ()


def test_key_works_in_a_dict():
    cache = {}
    cache[cache_key({"tags": ["go"], "page": 1})] = "cached page"
    assert cache[cache_key({"page": 1, "tags": ["go"]})] == "cached page"


def test_params_are_not_changed():
    params = {"tags": ["go", "py"], "q": "x"}
    cache_key(params)
    assert params == {"tags": ["go", "py"], "q": "x"}
    assert type(params["tags"]) is list
