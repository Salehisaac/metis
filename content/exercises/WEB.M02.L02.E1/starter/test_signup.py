import importlib
import sys

import pytest
from pydantic import ValidationError

VALID = {"username": "sara_99", "display_name": "Sara", "password": "s3cret-pass", "password_confirm": "s3cret-pass"}


def model():
    sys.modules.pop("signup", None)
    return importlib.import_module("signup").SignupRequest


def errors(**changes):
    """(loc, type) pairs for VALID with some fields changed; [] if it validates."""
    try:
        model()(**(VALID | changes))
    except ValidationError as e:
        return [(err["loc"], err["type"]) for err in e.errors()]
    return []


def test_valid_signup_is_normalised():
    s = model()(**(VALID | {"username": "  Sara_99 ", "display_name": "  Sara K  "}))
    assert (s.username, s.display_name) == ("sara_99", "Sara K")
    assert s.password == "s3cret-pass"


def test_username_is_normalised_before_length_and_pattern_checks():
    assert errors(username="  ab  ") == [(("username",), "string_too_short")]
    assert errors(username="ALI") == []
    assert errors(username="a" * 20) == []
    assert errors(username="a" * 21) == [(("username",), "string_too_long")]


def test_username_allowed_characters():
    for bad in ["ali-k", "ali k", "علی", "ali!"]:
        assert errors(username=bad) == [(("username",), "string_pattern_mismatch")], bad


def test_username_that_is_not_a_string():
    assert errors(username=123) == [(("username",), "string_type")]


def test_display_name_is_stripped_then_checked():
    assert errors(display_name="   ") == [(("display_name",), "string_too_short")]
    assert errors(display_name="x" * 50) == []
    assert errors(display_name="x" * 51) == [(("display_name",), "string_too_long")]


def test_password_length():
    assert errors(password="abc1234", password_confirm="abc1234") == [(("password",), "string_too_short")]
    long = "a1" * 32
    assert errors(password=long, password_confirm=long) == []
    assert errors(password=long + "x", password_confirm=long + "x") == [(("password",), "string_too_long")]


@pytest.mark.parametrize("pw", ["longpassword", "12345678", "--------"])
def test_password_needs_a_letter_and_a_digit(pw):
    with pytest.raises(ValidationError) as info:
        model()(**(VALID | {"password": pw, "password_confirm": pw}))
    [err] = info.value.errors()
    assert (err["loc"], err["type"]) == (("password",), "value_error")
    assert "letter and a digit" in err["msg"]


def test_password_is_not_stripped():
    s = model()(**(VALID | {"password": " pass word 1 ", "password_confirm": " pass word 1 "}))
    assert s.password == " pass word 1 "


def test_confirmation_must_match():
    with pytest.raises(ValidationError) as info:
        model()(**(VALID | {"password_confirm": "s3cret-pasS"}))
    [err] = info.value.errors()
    assert (err["loc"], err["type"]) == ((), "value_error")
    assert "passwords do not match" in err["msg"]


def test_no_mismatch_error_when_password_itself_is_invalid():
    assert errors(password="short", password_confirm="other") == [(("password",), "string_too_short")]


def test_unknown_fields_are_rejected():
    assert errors(is_admin=True) == [(("is_admin",), "extra_forbidden")]
