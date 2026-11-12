"""Runs the team's Ruff checks on pricing.py and checks its behaviour didn't change (or got fixed)."""
import importlib
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

HERE = Path(__file__).parent


def ruff(*args):
    """Run the venv's Ruff on pricing.py with this folder's pyproject.toml; returns (exit code, output)."""
    r = subprocess.run([sys.executable, "-m", "ruff", *args, "--no-cache", "pricing.py"],
                       cwd=HERE, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def load():
    sys.modules.pop("pricing", None)
    return importlib.import_module("pricing")


def test_ruff_check_passes():
    code, out = ruff("check", "--output-format", "concise")
    assert code == 0, f"ruff check found problems:\n{out}"


def test_ruff_format_check_passes():
    code, out = ruff("format", "--check")
    assert code == 0, f"ruff format --check wants changes:\n{out}"


def test_no_rules_switched_off():
    cfg = tomllib.loads((HERE / "pyproject.toml").read_text(encoding="utf-8"))
    lint = cfg["tool"]["ruff"]["lint"]
    assert set(lint["select"]) >= {"E", "F", "I", "B", "UP"}, "keep the selected rules"
    assert not lint.get("ignore") and not lint.get("per-file-ignores"), "fix the code instead of ignoring rules"
    assert "noqa" not in (HERE / "pricing.py").read_text(encoding="utf-8"), "no noqa comments"


def test_totals_are_unchanged():
    p = load()
    assert p.basket_total([1000, 500]) == 1500
    assert p.basket_total([1000, 500], ["welcome"]) == 1350
    assert p.basket_total([1000], ["WELCOME", "VIP"]) == 750
    assert p.basket_total([]) == 0


def test_codes_argument_is_not_mutated():
    p = load()
    codes = ["VIP"]
    p.basket_total([100], codes)
    assert codes == ["VIP"], "basket_total must not modify the caller's list"
    p.basket_total([100])
    p.basket_total([100])
    assert p.basket_total.__defaults__ in (None, (None,)), "a list default is shared between calls"


def test_only_unknown_codes_are_swallowed():
    p = load()
    assert p.discount_for("nope") == 0
    with pytest.raises(AttributeError):
        p.discount_for(None)
