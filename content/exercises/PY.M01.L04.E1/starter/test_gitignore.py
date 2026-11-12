"""Checks .gitignore with real Git: each test builds a throwaway repository using it."""
import os
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
GIT = shutil.which("git")
# Ignore your personal Git config (a global excludesFile could hide files and make tests pass wrongly).
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def make_repo(tmp_path, files):
    assert GIT, "git must be installed for this exercise"
    subprocess.run([GIT, "init", "-q", str(tmp_path)], check=True, env=ENV)
    shutil.copy(HERE / ".gitignore", tmp_path / ".gitignore")
    for name in files:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    return tmp_path


def ignored(repo, name):
    """True if Git ignores the path (git check-ignore exits 0 for ignored paths)."""
    return subprocess.run([GIT, "-C", str(repo), "check-ignore", "-q", name], env=ENV).returncode == 0


def test_ignores_the_virtualenv(tmp_path):
    repo = make_repo(tmp_path, [".venv/lib/python3.12/site.py", "PY.M01.L01.E1/.venv/bin/python"])
    assert ignored(repo, ".venv/lib/python3.12/site.py")
    assert ignored(repo, "PY.M01.L01.E1/.venv/bin/python")


def test_ignores_python_caches(tmp_path):
    files = ["__pycache__/words.cpython-312.pyc", "PY.M01.L01.E1/__pycache__/wordcount.cpython-312.pyc",
             "old.pyc", ".pytest_cache/v/cache/nodeids"]
    repo = make_repo(tmp_path, files)
    for name in files:
        assert ignored(repo, name), name


def test_ignores_test_reports_anywhere(tmp_path):
    repo = make_repo(tmp_path, ["result.xml", "PY.M01.L03.E1/result.xml"])
    assert ignored(repo, "result.xml")
    assert ignored(repo, "PY.M01.L03.E1/result.xml")


def test_keeps_your_code(tmp_path):
    files = ["words.py", "test_words.py", "PY.M01.L01.E1/wordcount.py", "PY.M01.L03.E1/test_initials.py", "notes.md"]
    repo = make_repo(tmp_path, files)
    for name in files + [".gitignore"]:
        assert not ignored(repo, name), f"{name} must not be ignored"
