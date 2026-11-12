"""Check every exercise's tests are meaningful. Stdlib + pytest (run via the current interpreter).

For each content/exercises/<ID>/:
  starter code   -> tests must FAIL (failures > 0) and must not ERROR (errors == 0: an import or
                    collection error "fails" for the wrong reason)
  starter + solution overlay -> every test must pass (tests > 0, failures == errors == 0)
Usage: .venv/bin/python tools/check_exercises.py
"""

import json
import shutil
import subprocess
import sys
import tempfile
# Parses only result.xml that pytest itself just wrote into our temp dir (trusted input), so stdlib ET
# is fine here. Learner-supplied XML is parsed only in the browser (DOMParser, no external entities).
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scaffold import ROOT, pytest_ini  # noqa: E402


def run_suite(workdir, exercise_id):
    (workdir / "pytest.ini").write_text(pytest_ini(exercise_id), encoding="utf-8")
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                   cwd=workdir, capture_output=True, text=True, timeout=120)
    suite = ET.parse(workdir / "result.xml").getroot()
    suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
    names = sorted(tc.get("name") for tc in suite.iter("testcase"))
    return {k: int(suite.get(k, 0)) for k in ("tests", "failures", "errors", "skipped")} | {"name": suite.get("name"), "cases": names}


def check(exercise_dir):
    ex_id = exercise_dir.name
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "w"
        shutil.copytree(exercise_dir / "starter", work)
        r = run_suite(work, ex_id)
        if r["name"] != ex_id:
            problems.append(f"junit suite name {r['name']!r} != {ex_id!r}")
        if r["errors"] or not r["failures"]:
            problems.append(f"starter should fail cleanly, got {r}")
        expected = sorted(json.loads((exercise_dir / "exercise.json").read_text(encoding="utf-8")).get("tests", []))
        if r["cases"] != expected:
            problems.append(f"starter test names {r['cases']} != exercise.json tests {expected}")
        for f in (exercise_dir / "solution").iterdir():  # every solution file (incl. dotfiles), not the write-up
            if f.is_file() and f.name != "SOLUTION.md":
                shutil.copy(f, work / f.name)
        r = run_suite(work, ex_id)
        if not r["tests"] or r["failures"] or r["errors"]:
            problems.append(f"reference solution should pass all tests, got {r}")
    leaks = leaked_lines(exercise_dir)
    if len(leaks) >= LEAK_LIMIT:
        problems.append(f"lesson shows {len(leaks)} solution lines verbatim before the exercise is attempted: {leaks}")
    return problems


# Solution lines that aren't already in the starter must not be printed in the lesson (spec §2.7: no solutions
# before an attempt). Short, comment and import lines are ignored; a couple of shared idioms (e.g. the __main__
# guard the lesson teaches) are tolerated, LEAK_LIMIT or more is a leak.
# ponytail: exact-line matching; paraphrased leaks (prose, renamed variables) still need a human read.
LEAK_LIMIT = 3


def _significant(lines):
    return {s for s in (x.strip() for x in lines) if len(s) >= 12 and not s.startswith(("#", "import ", "from "))}


def leaked_lines(exercise_dir):
    ex = json.loads((exercise_dir / "exercise.json").read_text(encoding="utf-8"))
    lesson = exercise_dir.parent.parent / "lessons" / f"{ex.get('lesson')}.md"
    if not lesson.is_file():
        return []
    starter = set()
    for f in (exercise_dir / "starter").iterdir():
        if f.is_file():
            starter |= _significant(f.read_text(encoding="utf-8").splitlines())
    solution = set()
    for f in (exercise_dir / "solution").iterdir():
        if f.is_file() and f.name != "SOLUTION.md":
            solution |= _significant(f.read_text(encoding="utf-8").splitlines())
    shown = _significant(lesson.read_text(encoding="utf-8").splitlines())
    return sorted((solution - starter) & shown)


def main(content=ROOT / "content"):
    dirs = sorted(p for p in (content / "exercises").glob("*") if p.is_dir())
    bad = 0
    for d in dirs:
        problems = check(d)
        bad += bool(problems)
        print(f"{d.name}: {'OK' if not problems else '; '.join(problems)}")
    print(f"{len(dirs)} exercise(s), {bad} with problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "content"))
