"""Checks YOUR tests in test_failures.py. Don't edit this file.

Each mutant is app.py with one realistic bug, made of (text in app.py, replacement) edits.
A mutant is killed when at least one of your tests fails against it.
"""

import gc
import importlib
import inspect
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from conftest import Connections, make_engine

SOURCE = (Path(__file__).parent / "app.py").read_text(encoding="utf-8")

MUTANTS = {
    "commit_per_step": [("            session.add(message)\n",
                         "            session.add(message)\n            session.commit()\n")],
    "conflict_is_500": [("except IntegrityError:", "except KeyError:")],
    "session_leak": [("    with request.app.state.session_factory() as session:\n        yield session\n",
                      "    session = request.app.state.session_factory()\n    yield session\n")],
    "commit_after_yield": [("            session.commit()\n", ""),
                           ("        yield session\n", "        yield session\n        session.commit()\n")],
    "count_not_updated": [("            chat.message_count += 1\n", "")],
}


def _module_from(source):
    module = type(sys)("app")
    exec(compile(source, "app.py", "exec"), module.__dict__)
    return module


def _run(test, api):
    with tempfile.TemporaryDirectory() as tmp:
        engine = make_engine(api, Path(tmp) / "meta.db")
        fixtures = {"engine": engine, "connections": Connections(engine)}
        with Session(engine) as db, TestClient(api.create_app(engine)) as client:
            fixtures.update(db=db, client=client)
            test(**{name: fixtures[name] for name in inspect.signature(test).parameters})
        engine.dispose()


def failing_tests(source):
    real = sys.modules.get("app")
    api = sys.modules["app"] = _module_from(source)
    gc.disable()  # a leaked session must stay leaked until the test checks the pool
    try:
        tests = importlib.reload(importlib.import_module("test_failures"))
        failed = []
        for name in sorted(n for n in vars(tests) if n.startswith("test_")):
            try:
                _run(getattr(tests, name), api)
            except (Exception, pytest.fail.Exception):
                failed.append(name)
        return failed
    finally:
        gc.enable()
        sys.modules["app"] = real
        importlib.reload(importlib.import_module("test_failures"))


def _apply(edits):
    source = SOURCE
    for old, new in edits:
        assert source.count(old) == 1, "app.py was edited: restore the original"
        source = source.replace(old, new)
    return source


@pytest.mark.parametrize("mutant", MUTANTS)
def test_tests_kill(mutant):
    mutated = _apply(MUTANTS[mutant])
    on_real = failing_tests(SOURCE)
    assert not on_real, f"these tests fail on the REAL app.py, fix them first: {on_real}"
    assert failing_tests(mutated), f"no test fails on mutant {mutant!r}: {MUTANTS[mutant]}"
