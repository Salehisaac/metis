import io
import itertools


def tracked(lines, pulled):
    """A source that records every line the pipeline pulls from it."""
    for line in lines:
        pulled.append(line)
        yield line


def endless(items, limit=1000):
    """Repeat items forever, but fail loudly if a stage pulls far more than it needs (not lazy)."""
    for pulled, item in enumerate(itertools.cycle(items)):
        if pulled >= limit:
            raise AssertionError(f"pulled {limit} items from an endless source: a stage isn't lazy")
        yield item


def test_parse_basic():
    from logpipe import parse_lines
    assert list(parse_lines(["ERROR db timeout", "info started"])) == [
        ("ERROR", "db timeout"),
        ("INFO", "started"),
    ]


def test_parse_skips_blank_and_comment_lines():
    from logpipe import parse_lines
    lines = ["", "   ", "# deploy 42", "  WARN  disk 91%  "]
    assert list(parse_lines(lines)) == [("WARN", "disk 91%")]


def test_parse_level_without_message():
    from logpipe import parse_lines
    assert list(parse_lines(["DEBUG"])) == [("DEBUG", "")]


def test_parse_reads_file_lines():
    from logpipe import parse_lines
    f = io.StringIO("ERROR a\n\nINFO b c\n")
    assert list(parse_lines(f)) == [("ERROR", "a"), ("INFO", "b c")]


def test_parse_is_lazy():
    from logpipe import parse_lines
    pulled = []
    records = parse_lines(tracked(["ERROR a", "INFO b"], pulled))
    assert pulled == [], "nothing should be read before the first next()"
    assert next(records) == ("ERROR", "a")
    assert pulled == ["ERROR a"], "one record needs only one line"


def test_only_level_is_case_insensitive():
    from logpipe import only_level
    records = [("ERROR", "a"), ("INFO", "b"), ("ERROR", "c")]
    assert list(only_level(records, "error")) == [("ERROR", "a"), ("ERROR", "c")]
    assert list(only_level(records, "WARN")) == []


def test_first_n_does_not_pull_extra_items():
    from logpipe import first_n
    it = iter([1, 2, 3, 4])
    assert list(first_n(it, 2)) == [1, 2]
    assert next(it) == 3, "first_n pulled one item too many"


def test_first_n_zero_or_negative_pulls_nothing():
    from logpipe import first_n
    it = iter([1, 2])
    assert list(first_n(it, 0)) == []
    assert list(first_n(it, -1)) == []
    assert next(it) == 1


def test_first_n_shorter_input():
    from logpipe import first_n
    assert list(first_n([7], 5)) == [7]
    assert list(first_n([], 3)) == []


def test_first_n_on_endless_input():
    from logpipe import first_n
    assert list(first_n(endless([0, 1, 2, 3]), 3)) == [0, 1, 2]


def test_pipeline_on_endless_log():
    from logpipe import first_n, only_level, parse_lines
    log = endless(["INFO ok", "", "ERROR boom", "# note"])
    errors = first_n(only_level(parse_lines(log), "error"), 3)
    assert list(errors) == [("ERROR", "boom")] * 3
