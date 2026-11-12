import pytest


def test_valid_record():
    from scores import parse_record
    assert parse_record("ada,42", 1) == ("ada", 42)


def test_spaces_around_fields():
    from scores import parse_record
    assert parse_record("  grace , 7 ", 2) == ("grace", 7)


def test_missing_comma():
    from scores import BadRecord, parse_record
    with pytest.raises(BadRecord, match="line 3: expected 'name,score', got 'ada 42'"):
        parse_record("ada 42", 3)


def test_too_many_commas():
    from scores import BadRecord, parse_record
    with pytest.raises(BadRecord, match="line 4: expected 'name,score', got 'a,b,c'"):
        parse_record("a,b,c", 4)


def test_empty_name():
    from scores import BadRecord, parse_record
    with pytest.raises(BadRecord, match="line 5: expected 'name,score', got ' ,5'"):
        parse_record(" ,5", 5)


def test_bad_score_keeps_the_cause():
    from scores import BadRecord, parse_record
    with pytest.raises(BadRecord, match="line 6: bad score 'x'") as excinfo:
        parse_record("ada, x", 6)
    assert isinstance(excinfo.value.__cause__, ValueError)


def test_load_counts_skipped_lines():
    from scores import load_scores
    assert load_scores(["ada,3", "oops", "bob,5", "c,d"]) == ({"ada": 3, "bob": 5}, 2)


def test_load_ignores_blank_lines():
    from scores import load_scores
    assert load_scores(["ada,3", "", "   ", "bob,5"]) == ({"ada": 3, "bob": 5}, 0)


def test_load_empty_input():
    from scores import load_scores
    assert load_scores([]) == ({}, 0)


def test_bugs_are_not_swallowed():
    from scores import load_scores
    # None is not a line: that's a bug in the caller, not a malformed record.
    # It must surface as the original error, not be counted as skipped.
    with pytest.raises(AttributeError):
        load_scores(["ada,3", None])
