import pytest


def test_plain_number():
    from port import parse_port
    assert parse_port("8080") == 8080


def test_surrounding_whitespace_is_ignored():
    from port import parse_port
    assert parse_port(" 443\n") == 443


def test_limits_are_valid():
    from port import parse_port
    assert (parse_port("1"), parse_port("65535")) == (1, 65535)


def test_not_a_number():
    from port import PortError, parse_port
    with pytest.raises(PortError, match="invalid port 'http'"):
        parse_port("http")


def test_empty_string():
    from port import PortError, parse_port
    with pytest.raises(PortError, match="invalid port ''"):
        parse_port("")


def test_not_a_number_keeps_the_cause():
    from port import PortError, parse_port
    with pytest.raises(PortError) as excinfo:
        parse_port("80a")
    # like %w in Go: the original int() error is attached as the cause
    assert isinstance(excinfo.value.__cause__, ValueError)


def test_zero_is_out_of_range():
    from port import PortError, parse_port
    with pytest.raises(PortError, match="port 0 out of range 1-65535"):
        parse_port("0")


def test_too_big():
    from port import PortError, parse_port
    with pytest.raises(PortError, match="port 65536 out of range 1-65535"):
        parse_port("65536")


def test_negative():
    from port import PortError, parse_port
    with pytest.raises(PortError, match="port -1 out of range 1-65535"):
        parse_port("-1")


def test_range_error_has_no_cause():
    from port import PortError, parse_port
    with pytest.raises(PortError) as excinfo:
        parse_port("70000")
    assert excinfo.value.__cause__ is None


def test_callers_can_catch_value_error():
    from port import PortError, parse_port
    assert issubclass(PortError, ValueError)
    with pytest.raises(ValueError):
        parse_port("ssh")
