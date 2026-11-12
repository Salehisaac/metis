"""Create a learner workspace for an exercise. Stdlib only.

Usage: python tools/scaffold.py PY.M01.L01.E1
Copies the starter files (never the reference solution) to workspace/<ID>/ and writes a pytest.ini
that names the JUnit suite after the exercise, so imported results can be matched to it.
Refuses to touch an existing workspace: that folder is the learner's work.
"""

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXERCISE_ID = re.compile(r"^[A-Z]+\.M\d{2}\.L\d{2}\.E\d+$")


def pytest_ini(exercise_id):
    return (
        "[pytest]\n"
        f"junit_suite_name = {exercise_id}\n"
        "junit_family = xunit2\n"
        "addopts = --junitxml=result.xml\n"
    )


def scaffold(exercise_id, content=ROOT / "content", workspace=ROOT / "workspace"):
    if not EXERCISE_ID.match(exercise_id):
        raise ValueError(f"not an exercise id: {exercise_id!r}")
    starter = content / "exercises" / exercise_id / "starter"
    if not starter.is_dir():
        raise FileNotFoundError(f"no starter files for {exercise_id}")
    dest = workspace / exercise_id
    if dest.exists():
        raise FileExistsError(f"{dest} already exists; not overwriting your work")
    shutil.copytree(starter, dest)
    (dest / "pytest.ini").write_text(pytest_ini(exercise_id), encoding="utf-8")
    return dest


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    try:
        dest = scaffold(argv[0])
    except (ValueError, FileNotFoundError, FileExistsError) as e:
        print(f"error: {e}")
        return 1
    print(f"created {dest.relative_to(ROOT)}\nnext: cd {dest.relative_to(ROOT)} && ../../.venv/bin/pytest")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
