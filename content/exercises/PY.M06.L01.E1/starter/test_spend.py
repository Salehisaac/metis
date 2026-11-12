"""The tests build a real package from your files and run it the way a user would.

Each test copies every .py file in this folder (except the tests) into a temporary folder
<tmp>/<package name>/, adds an empty __init__.py, and runs Python in <tmp> with -m or -c.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SAMPLE = "2026-11-01,food,12.50\n\n2026-11-02,rent,700\n2026-11-03, food ,7.25\n"


def build(tmp_path, name="spend"):
    pkg = tmp_path / name
    pkg.mkdir()
    for f in HERE.glob("*.py"):
        if not f.name.startswith("test_") and f.name != "conftest.py":
            shutil.copy(f, pkg / f.name)
    (pkg / "__init__.py").write_text("")
    (tmp_path / "expenses.csv").write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "empty.csv").write_text("", encoding="utf-8")
    return tmp_path


def run(cwd, *args):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_report_imports_first(tmp_path):
    r = run(build(tmp_path), "-c", "import spend.report")
    assert r.returncode == 0, r.stderr


def test_ledger_imports_first(tmp_path):
    r = run(build(tmp_path), "-c", "import spend.ledger")
    assert r.returncode == 0, r.stderr


def test_runs_with_python_m(tmp_path):
    r = run(build(tmp_path), "-m", "spend", "expenses.csv")
    assert r.returncode == 0, r.stderr
    assert r.stdout == "food: 19.75 EUR\nrent: 700.00 EUR\n"


def test_empty_file(tmp_path):
    r = run(build(tmp_path), "-m", "spend", "empty.csv")
    assert r.returncode == 0, r.stderr
    assert r.stdout == "no expenses\n"


def test_missing_argument_exits_2(tmp_path):
    r = run(build(tmp_path), "-m", "spend")
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert "usage: python -m spend FILE" in r.stderr
    assert r.stdout == ""


def test_works_under_another_package_name(tmp_path):
    r = run(build(tmp_path, name="budget"), "-m", "budget", "expenses.csv")
    assert r.returncode == 0, r.stderr
    assert r.stdout == "food: 19.75 EUR\nrent: 700.00 EUR\n"
