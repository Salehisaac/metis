"""YOUR tests for parse_duration. Its docstring in duration.py is the spec.

1. Add rows to VALID and INVALID. Keep the rows that are already here: the exercise
   looks for their test names in your result.xml.
2. Write test_invalid (see the TODO below).
3. test_meta.py checks your tables against six buggy versions of parse_duration.
   Don't edit it. Every bug must make at least one of your rows fail.
"""

import pytest

from duration import parse_duration

VALID = [
    ("90s", 90),
    ("2m", 120),
    ("1h", 3600),             # hours: catches a wrong multiplier
    ("1h30m", 5400),          # two units together
    ("1h2m3s", 3723),         # all three units
    ("0s", 0),                # zero is valid: catches a truthiness check
    ("  5m ", 300),           # surrounding whitespace is ignored
]

INVALID = [
    "abc",
    "",                       # empty
    "   ",                    # blank: only whitespace
    "30m1h",                  # wrong order
    "1m1m",                   # unit repeated
    "10",                     # number without a unit
    "h",                      # unit without a number
    "1.5h",                   # decimal
    "-5s",                    # sign
    "1H",                     # uppercase unit
    "1h 30m",                 # inner space
]


@pytest.mark.parametrize("text, expected", VALID)
def test_valid(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text", INVALID)
def test_invalid(text):
    with pytest.raises(ValueError, match="invalid duration"):
        parse_duration(text)
