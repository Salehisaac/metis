import importlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "wordcount.py"


def load():
    """Import wordcount fresh (import runs the file)."""
    sys.modules.pop("wordcount", None)
    return importlib.import_module("wordcount")


def test_import_prints_nothing(capsys):
    load()
    assert capsys.readouterr().out == "", "importing wordcount should not print anything"


def test_main_prints_count_and_returns_0(capsys):
    wc = load()
    capsys.readouterr()  # discard anything printed during import
    assert wc.main(["wordcount.py", "go", "py go"]) == 0
    assert capsys.readouterr().out == "3\n"


def test_script_counts_words():
    r = subprocess.run([sys.executable, str(SCRIPT), "a", "b"], capture_output=True, text=True)
    assert (r.returncode, r.stdout) == (0, "2\n")


def test_script_without_words_shows_usage():
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 2
    assert r.stdout == ""
    assert "usage" in r.stderr.lower()
