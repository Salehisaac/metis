"""Checks YOUR rows and tests in test_api.py. Don't edit this file.

Each mutant is app.py with one realistic bug: (text in app.py, replacement).
A mutant is killed when at least one CASES row gets a different status code from it,
or one of your other tests fails on it. Read the mutants only after your first run.
"""

import importlib
import sys
from pathlib import Path

import pytest

from conftest import make_client

SOURCE = (Path(__file__).parent / "app.py").read_text(encoding="utf-8")

MUTANTS = {
    "limit_zero_allowed": ("Query(ge=1, le=100)", "Query(ge=0, le=100)"),
    "limit_max_too_high": ("Query(ge=1, le=100)", "Query(ge=1, le=1000)"),
    "text_too_long_allowed": ("max_length=500", "max_length=5000"),
    "delete_returns_200": ("status_code=204", "status_code=200"),
    "delete_ignores_chat": ("if m.chat_id == chat_id and m.id == message_id:", "if m.id == message_id:"),
    "list_unknown_chat_200": ("    require_chat(store, chat_id)\n    in_chat", "    in_chat"),
    "no_503_handler": ("    app.add_exception_handler(StoreUnavailable, store_unavailable)\n", ""),
}


def _module_from(source):
    module = type(sys)("app")
    exec(compile(source, "app.py", "exec"), module.__dict__)
    return module


def problems_on(source):
    """Rows whose status differs on `source`, plus your other tests that fail on it."""
    real = sys.modules.get("app")
    api = sys.modules["app"] = _module_from(source)
    try:
        tests = importlib.reload(importlib.import_module("test_api"))
        found = []
        for case in tests.CASES:
            method, url, body, expected = case.values
            try:
                got = make_client(api).request(method, url, json=body).status_code
            except Exception as exc:
                got = type(exc).__name__
            if got != expected:
                found.append(f"{case.id}: got {got}, row expects {expected}")
        for name in sorted(n for n in vars(tests) if n.startswith("test_") and n != "test_status"):
            try:
                getattr(tests, name)(make_client(api))
            except (Exception, pytest.fail.Exception):
                found.append(f"{name} fails")
        return found
    finally:
        sys.modules["app"] = real
        importlib.reload(importlib.import_module("test_api"))


@pytest.mark.parametrize("mutant", MUTANTS)
def test_tests_kill(mutant):
    old, new = MUTANTS[mutant]
    assert SOURCE.count(old) == 1, "app.py was edited: restore the original"
    on_real = problems_on(SOURCE)
    assert not on_real, f"fix these against the REAL app.py first: {on_real}"
    assert problems_on(SOURCE.replace(old, new)), f"nothing fails on mutant {mutant!r}: {old!r} -> {new!r}"
