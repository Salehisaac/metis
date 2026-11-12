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
]

INVALID = [
    "abc",
]


@pytest.mark.parametrize("text, expected", VALID)
def test_valid(text, expected):
    assert parse_duration(text) == expected


# TODO: write test_invalid(text), parametrized over INVALID.
# It must check that parse_duration(text) raises ValueError
# with a message matching "invalid duration" (use pytest.raises with match=).
