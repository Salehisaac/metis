"""Behaviour tests plus two Ruff checks.

The Ruff tests run the ruff installed in this academy's .venv (ruff==0.17.3) as
`python -m ruff`, with --isolated so that no config file can change the rules.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
RULES = ["--select", "E,F,W,B,I,UP,SIM", "--target-version", "py312"]


def ruff(*args):
    assert importlib.util.find_spec("ruff"), (
        "ruff isn't installed in this interpreter's venv"
    )
    return subprocess.run(
        [sys.executable, "-m", "ruff", *args, "--isolated", "--no-cache"],
        cwd=HERE,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_ruff_check_passes():
    r = ruff("check", "--output-format", "concise", *RULES, "invoice.py")
    assert r.returncode == 0, r.stdout + r.stderr


def test_ruff_format_check_passes():
    r = ruff("format", "--check", "invoice.py")
    assert r.returncode == 0, r.stdout + r.stderr


def test_no_suppression_comments():
    source = (HERE / "invoice.py").read_text(encoding="utf-8")
    assert "noqa" not in source and "ruff:" not in source, (
        "fix the code instead of silencing Ruff"
    )


def test_add_line_appends_to_given_list():
    from invoice import add_line

    lines = [("tea", 3.5)]
    assert add_line("cake", 4.0, lines) is lines
    assert lines == [("tea", 3.5), ("cake", 4.0)]


def test_add_line_starts_fresh_each_call():
    from invoice import add_line

    assert add_line("tea", 3.5) == [("tea", 3.5)]
    assert add_line("cake", 4.0) == [("cake", 4.0)]


def test_parse_price():
    from invoice import parse_price

    assert parse_price("12.50") == 12.5
    assert parse_price(" 7 ") == 7.0
    assert parse_price("abc") is None
    assert parse_price("") is None


def test_total():
    from invoice import total

    assert total([("tea", 0.1), ("cake", 0.2)]) == 0.3
    assert total([]) == 0.0


def test_is_free_and_describe():
    from invoice import describe, is_free

    assert is_free(0) is True
    assert is_free(0.01) is False
    assert describe("tea", 3.5) == "tea: 3.50"
    assert describe("tea", 0) == "tea: 0.00"
    assert describe("tea", None) == "tea: ?"
