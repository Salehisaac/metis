import pytest

from settings import parse_list, parse_settings

CONFIG = """
# database
db_host = localhost
db_port=5432

  # indented comment
dsn = user=app password=s3cret
debug =
hosts = a.example, b.example,,c.example ,
"""


def test_parses_keys_and_values():
    result = parse_settings(CONFIG)
    assert result["db_host"] == "localhost"
    assert result["db_port"] == "5432"


def test_skips_blank_lines_and_comments():
    assert list(parse_settings(CONFIG)) == ["db_host", "db_port", "dsn", "debug", "hosts"]


def test_value_may_contain_equals():
    assert parse_settings(CONFIG)["dsn"] == "user=app password=s3cret"


def test_empty_value_is_allowed():
    assert parse_settings(CONFIG)["debug"] == ""


def test_whitespace_only_lines_and_tabs():
    assert parse_settings("\t\n   \n\tname\t=\tmetis  \n") == {"name": "metis"}


def test_later_key_overrides():
    assert parse_settings("mode = dev\nmode = prod") == {"mode": "prod"}


def test_empty_text():
    assert parse_settings("") == {}


def test_line_without_equals_raises_with_line_number():
    with pytest.raises(ValueError, match="3"):
        parse_settings("a = 1\n\njust some words\n")


def test_empty_key_raises():
    with pytest.raises(ValueError):
        parse_settings(" = value")


def test_parse_list():
    assert parse_list(parse_settings(CONFIG)["hosts"]) == ["a.example", "b.example", "c.example"]


def test_parse_list_keeps_inner_spaces():
    assert parse_list("New York, Tehran") == ["New York", "Tehran"]


def test_parse_list_empty_and_blank():
    assert parse_list("") == []
    assert parse_list(" , ,") == []
