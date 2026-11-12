"""Checks YOUR tests in test_messages.py. Don't edit this file.

Each mutant below is app.py with one realistic bug: (text in app.py, replacement).
A good test suite passes on the real app.py and "kills" every mutant: at least one of
your tests fails when it runs against that mutant.
Read the mutants only after your first run, and try to predict which of your tests kills each one.
"""

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SOURCE = (Path(__file__).parent / "app.py").read_text(encoding="utf-8")

MUTANTS = {
    "created_is_200": ("status_code=201", "status_code=200"),
    "unknown_chat_accepted": ("    require_chat(store, chat_id)\n    message = ", "    message = "),
    "blank_accepted": ("if not value.strip():", "if not value:"),
    "wrong_chat_id": ("chat_id=chat_id, text=body.text", "chat_id=1, text=body.text"),
    "other_chats_listed": ("[m for m in store.messages if m.chat_id == chat_id]", "list(store.messages)"),
    "newest_first": ("return in_chat[-limit:]", "return in_chat[::-1][:limit]"),
}


def _module_from(source):
    module = type(sys)("app")
    exec(compile(source, "app.py", "exec"), module.__dict__)
    return module


def failing_tests(source):
    """Run every test_* in test_messages.py against `source`; return the names that fail."""
    real = sys.modules.get("app")
    sys.modules["app"] = _module_from(source)
    try:
        tests = importlib.reload(importlib.import_module("test_messages"))
        failed = []
        for name in sorted(n for n in vars(tests) if n.startswith("test_")):
            client = TestClient(sys.modules["app"].create_app())
            try:
                getattr(tests, name)(client)
            except (Exception, pytest.fail.Exception):
                failed.append(name)
        return failed
    finally:
        sys.modules["app"] = real
        importlib.reload(importlib.import_module("test_messages"))


@pytest.mark.parametrize("mutant", MUTANTS)
def test_tests_kill(mutant):
    old, new = MUTANTS[mutant]
    assert SOURCE.count(old) == 1, "app.py was edited: restore the original"
    on_real = failing_tests(SOURCE)
    assert not on_real, f"these tests fail on the REAL app.py, fix them first: {on_real}"
    assert failing_tests(SOURCE.replace(old, new)), f"no test fails on mutant {mutant!r}: {old!r} -> {new!r}"
