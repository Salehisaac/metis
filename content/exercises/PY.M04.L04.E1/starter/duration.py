"""The code under test. It is correct; don't change it. Your job is the tests."""

import re

_DURATION = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")


def parse_duration(text: str) -> int:
    """Parse a duration like '1h30m' into a number of seconds.

    Spec:
    - Surrounding whitespace is ignored: ' 5m ' is 300.
    - The text is one or more groups of <digits><unit>, where unit is h, m or s.
    - Each unit appears at most once, in the order h, m, s:
      '1h30m' and '1h5s' are fine; '30m1h' and '1m1m' are not.
    - Units are lowercase. No signs, decimals or inner spaces.
    - Values are not normalised: '90s' is 90 and '90m' is 5400.
    - Zero is a valid duration: '0s' is 0.
    - Anything else, including '' and '   ', raises ValueError("invalid duration: <the text, repr'd>").
    """
    stripped = text.strip()
    match = _DURATION.fullmatch(stripped)
    if not stripped or match is None:
        raise ValueError(f"invalid duration: {text!r}")
    hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds
