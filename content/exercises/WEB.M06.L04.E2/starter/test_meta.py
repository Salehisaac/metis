"""Checks YOUR table in test_access.py. Don't edit this file.

Each mutant is app.py with one realistic access-control bug: (text in app.py, replacement).
A mutant is killed when at least one CASES row gets a different status code from it.
Read the mutants only after your first run.
"""

import importlib
import sys
from pathlib import Path

import pytest

from conftest import headers, make_client

SOURCE = (Path(__file__).parent / "app.py").read_text(encoding="utf-8")

MUTANTS = {
    "member_can_rename": ("if user.id != chat.owner_id and user.role != \"admin\":",
                          "if user.id not in chat.member_ids and user.role != \"admin\":"),
    "admin_cannot_rename": ("if user.id != chat.owner_id and user.role != \"admin\":",
                            "if user.id != chat.owner_id:"),
    "outsider_gets_403": ("status_code=404, detail=\"chat not found\"", "status_code=403, detail=\"chat not found\""),
    "bad_token_is_403": ("status_code=401", "status_code=403"),
    "member_removes_others": ("        elif user.id != user_id:", "        elif False:"),
    "owner_can_be_removed": ("            if user_id == chat.owner_id:", "            if False:"),
    "outsider_lists_members": ("        chat = visible_chat(store, chat_id, user)\n        return sorted",
                               "        chat = store.chats[chat_id]\n        return sorted"),
}


def _module_from(source):
    module = type(sys)("app")
    exec(compile(source, "app.py", "exec"), module.__dict__)
    return module


def differing_rows(source):
    real = sys.modules.get("app")
    api = sys.modules["app"] = _module_from(source)
    try:
        rows = importlib.reload(importlib.import_module("test_access")).CASES
        found = []
        for case in rows:
            actor, method, url, body, expected = case.values
            try:
                got = make_client(api).request(method, url, json=body, headers=headers(actor)).status_code
            except Exception as exc:
                got = type(exc).__name__
            if got != expected:
                found.append(f"{case.id}: got {got}, row expects {expected}")
        return found
    finally:
        sys.modules["app"] = real
        importlib.reload(importlib.import_module("test_access"))


@pytest.mark.parametrize("mutant", MUTANTS)
def test_rows_kill(mutant):
    old, new = MUTANTS[mutant]
    assert SOURCE.count(old) == 1, "app.py was edited: restore the original"
    on_real = differing_rows(SOURCE)
    assert not on_real, f"fix these rows against the REAL app.py first: {on_real}"
    assert differing_rows(SOURCE.replace(old, new)), f"no row fails on mutant {mutant!r}: {old!r} -> {new!r}"
