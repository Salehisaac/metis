import importlib
import sys


def load():
    sys.modules.pop("chat_import", None)
    return importlib.import_module("chat_import")


GOOD = {"id": 1, "chat_id": 10, "sender": "ali", "text": "hi"}


def test_valid_row_is_converted_with_defaults():
    m = load()
    messages, problems = m.parse_rows([{"id": "7", "chat_id": "10", "sender": "sara", "text": "hello"}])
    assert problems == []
    assert len(messages) == 1
    msg = messages[0]
    assert isinstance(msg, m.ImportedMessage)
    assert msg.model_dump() == {"id": 7, "chat_id": 10, "sender": "sara", "text": "hello", "reply_to": None, "tags": []}


def test_optional_fields_accept_values_and_null():
    m = load()
    rows = [GOOD | {"reply_to": 3, "tags": ["work"]}, GOOD | {"id": 2, "reply_to": None}]
    messages, problems = m.parse_rows(rows)
    assert problems == []
    assert [(x.reply_to, x.tags) for x in messages] == [(3, ["work"]), (None, [])]


def test_every_error_of_a_row_is_reported():
    m = load()
    _, problems = m.parse_rows([{"id": "one", "chat_id": 10, "text": 5}])
    assert problems == [
        {"row": 0, "field": "id", "type": "int_parsing"},
        {"row": 0, "field": "sender", "type": "missing"},
        {"row": 0, "field": "text", "type": "string_type"},
    ]


def test_valid_rows_kept_and_row_numbers_match_input():
    m = load()
    rows = [GOOD, GOOD | {"id": 2, "chat_id": 1.5}, GOOD | {"id": 3}]
    messages, problems = m.parse_rows(rows)
    assert [x.id for x in messages] == [1, 3]
    assert problems == [{"row": 1, "field": "chat_id", "type": "int_from_float"}]


def test_unknown_field_is_a_problem():
    m = load()
    messages, problems = m.parse_rows([GOOD | {"is_admin": True}])
    assert messages == []
    assert problems == [{"row": 0, "field": "is_admin", "type": "extra_forbidden"}]


def test_nested_location_is_joined_with_dots():
    m = load()
    _, problems = m.parse_rows([GOOD | {"tags": ["a", 3, "c", None]}])
    assert problems == [
        {"row": 0, "field": "tags.1", "type": "string_type"},
        {"row": 0, "field": "tags.3", "type": "string_type"},
    ]


def test_row_that_is_not_an_object():
    m = load()
    messages, problems = m.parse_rows([GOOD, "garbage", None])
    assert [x.id for x in messages] == [1]
    assert problems == [
        {"row": 1, "field": "", "type": "model_type"},
        {"row": 2, "field": "", "type": "model_type"},
    ]


def test_empty_input():
    m = load()
    assert m.parse_rows([]) == ([], [])
