import pytest


def test_level_and_words():
    from logline import log_line
    assert log_line("info", "user", "logged", "in") == "INFO user logged in"


def test_level_only():
    from logline import log_line
    assert log_line("error") == "ERROR"


def test_fields_sorted_by_key():
    from logline import log_line
    assert log_line("info", "login", user="ada", ip="10.0.0.1") == "INFO login ip=10.0.0.1 user=ada"


def test_field_values_become_strings():
    from logline import log_line
    assert log_line("debug", "retry", attempt=3, ok=False) == "DEBUG retry attempt=3 ok=False"


def test_value_with_space_is_quoted():
    from logline import log_line
    assert log_line("info", "signup", name="Ada Lovelace") == 'INFO signup name="Ada Lovelace"'


def test_ts_goes_first():
    from logline import log_line
    assert log_line("warn", "disk", "full", ts="12:00:01") == "12:00:01 WARN disk full"


def test_ts_none_means_no_timestamp():
    from logline import log_line
    assert log_line("info", "ready", ts=None) == "INFO ready"


def test_ts_is_keyword_only():
    from logline import log_line
    # A third positional argument is just another word, never the timestamp.
    assert log_line("info", "boot", "12:00") == "INFO boot 12:00"


def test_fields_from_a_dict():
    from logline import log_line
    extra = {"status": 200, "path": "/health"}
    assert log_line("info", **extra) == "INFO path=/health status=200"


def test_missing_level_is_type_error():
    from logline import log_line
    with pytest.raises(TypeError):
        log_line()


def test_level_twice_is_type_error():
    from logline import log_line
    with pytest.raises(TypeError):
        log_line("info", level="debug")
