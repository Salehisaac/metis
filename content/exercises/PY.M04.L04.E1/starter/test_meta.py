"""Checks YOUR tables in test_duration.py. Don't edit this file.

Each bug_* function is parse_duration with one realistic bug seeded in.
A good table "kills" every one of them: at least one row gives a different
result on the buggy version (a wrong number, or ValueError raised / not raised).
"""

import inspect
import re

import pytest

PATTERN = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")


def _seconds(match, hour=3600):
    h, m, s = (int(g) if g else 0 for g in match.groups())
    return h * hour + m * 60 + s


def _fail(text):
    raise ValueError(f"invalid duration: {text!r}")


def bug_no_strip(text):
    """Forgets to strip surrounding whitespace."""
    match = PATTERN.fullmatch(text)
    if not text or match is None:
        _fail(text)
    return _seconds(match)


def bug_empty_accepted(text):
    """Forgets that a pattern of optional parts also matches the empty string."""
    match = PATTERN.fullmatch(text.strip())
    if match is None:
        _fail(text)
    return _seconds(match)


def bug_blank_accepted(text):
    """Checks for emptiness before stripping."""
    if not text:
        _fail(text)
    match = PATTERN.fullmatch(text.strip())
    if match is None:
        _fail(text)
    return _seconds(match)


def bug_zero_rejected(text):
    """Uses truthiness: a total of 0 looks like 'nothing parsed'."""
    match = PATTERN.fullmatch(text.strip())
    if match is None or not _seconds(match):
        _fail(text)
    return _seconds(match)


def bug_hours_as_minutes(text):
    """Multiplies hours by 60 instead of 3600."""
    stripped = text.strip()
    match = PATTERN.fullmatch(stripped)
    if not stripped or match is None:
        _fail(text)
    return _seconds(match, hour=60)


def bug_any_order(text):
    """Accepts units in any order, and more than once."""
    stripped = text.strip()
    if not re.fullmatch(r"(?:\d+[hms])+", stripped):
        _fail(text)
    factor = {"h": 3600, "m": 60, "s": 1}
    return sum(int(n) * factor[u] for n, u in re.findall(r"(\d+)([hms])", stripped))


BUGS = [bug_no_strip, bug_empty_accepted, bug_blank_accepted, bug_zero_rejected, bug_hours_as_minutes, bug_any_order]


def _values(row):
    """A row may be a plain value/tuple or a pytest.param(...)."""
    return tuple(row.values) if hasattr(row, "marks") else row


def _tables():
    import test_duration
    valid = [_values(row) for row in test_duration.VALID]
    invalid = [_values(row)[0] if hasattr(row, "marks") else row for row in test_duration.INVALID]
    return valid, invalid


def _behaves_differently(impl, valid, invalid):
    """True if at least one row exposes impl."""
    for text, expected in valid:
        try:
            if impl(text) != expected:
                return True
        except ValueError:
            return True
    for text in invalid:
        try:
            impl(text)
        except ValueError:
            continue
        return True
    return False


def test_rows_are_correct():
    from duration import parse_duration
    valid, invalid = _tables()
    for text, expected in valid:
        assert parse_duration(text) == expected, f"VALID row {text!r}: the spec gives {parse_duration(text)}"
    for text in invalid:
        with pytest.raises(ValueError):
            parse_duration(text)  # an INVALID row that the spec accepts


def test_invalid_uses_raises_with_match():
    import test_duration
    fn = getattr(test_duration, "test_invalid", None)
    assert fn is not None, "write test_invalid in test_duration.py"
    marks = [m for m in getattr(fn, "pytestmark", []) if m.name == "parametrize"]
    assert marks, "parametrize test_invalid with @pytest.mark.parametrize"
    argvalues = marks[0].args[1] if len(marks[0].args) > 1 else marks[0].kwargs.get("argvalues")
    assert argvalues is test_duration.INVALID, "test_invalid must be parametrized over INVALID"
    assert re.search(r"pytest\.raises\(\s*ValueError\s*,\s*match\s*=", inspect.getsource(fn)), \
        "use pytest.raises(ValueError, match=...)"


@pytest.mark.parametrize("bug", BUGS, ids=lambda f: f.__name__)
def test_tables_catch(bug):
    valid, invalid = _tables()
    assert _behaves_differently(bug, valid, invalid), f"no row exposes {bug.__name__}: {bug.__doc__}"
