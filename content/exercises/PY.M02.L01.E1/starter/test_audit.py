from audit import changed_fields, save_version


def test_changed_value_is_reported():
    old = {"name": "ali", "role": "dev"}
    new = {"name": "ali", "role": "lead"}
    assert changed_fields(old, new) == ["role"]


def test_equal_lists_are_not_a_change():
    # Two separate list objects with the same items: same value, different objects.
    old = {"name": "ali", "langs": ["go", "py"]}
    new = {"name": "ali", "langs": ["go", "py"]}
    assert changed_fields(old, new) == []


def test_result_follows_old_key_order():
    old = {"a": 1, "b": [1], "c": "x"}
    new = {"a": 2, "b": [2], "c": "y"}
    assert changed_fields(old, new) == ["a", "b", "c"]


def test_none_values():
    old = {"phone": None, "email": None}
    new = {"phone": None, "email": "a@example.com"}
    assert changed_fields(old, new) == ["email"]


def test_empty_records():
    assert changed_fields({}, {}) == []


def test_history_grows_in_place():
    history = []
    save_version(history, {"name": "ali"})
    save_version(history, {"name": "bob"})
    assert history == [{"name": "ali"}, {"name": "bob"}]


def test_snapshot_survives_later_changes():
    history = []
    record = {"name": "ali", "role": "dev"}
    save_version(history, record)
    record["role"] = "lead"
    save_version(history, record)
    assert history == [{"name": "ali", "role": "dev"}, {"name": "ali", "role": "lead"}]


def test_snapshot_is_a_different_object():
    history = []
    record = {"name": "ali"}
    save_version(history, record)
    assert history[0] == record
    assert history[0] is not record
