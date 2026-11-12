"""Check one module's content before its flags are merged into curriculum.json (safe while other modules are in progress).

Usage: .venv/bin/python tools/check_module.py PY.M02 content/_pending/PY.M02.json
       .venv/bin/python tools/check_module.py PROJECTS content/_pending/PROJECTS.json
flags file: {"newLessons": [{"id": "DB.M01.L01", "title": "..."}],      # only for modules with no lessons defined yet
             "lessons": {"PY.M02.L01": {"exercises": ["PY.M02.L01.E1"], "quizzes": ["q1", "q2"]}, ...},
             "assessment": true}
projects file: {"projects": {"PRJ-02": true}}   # marks specified; content/projects/PRJ-02.md must exist
Applies the flags to an in-memory copy of curriculum.json, then reports only this module's problems from:
the content validator, the exercise checker (incl. the solution-leak check) and the output-quiz answer checker.
"""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_exercises  # noqa: E402
import check_quizzes  # noqa: E402
import validate  # noqa: E402

ROOT = validate.ROOT
CONTENT = ROOT / "content"


def apply(cur, module_id, flags):
    """Apply one pending flags file to a curriculum dict (also used by tools/merge_pending.py)."""
    if module_id == "PROJECTS":
        for p in cur["projects"]:
            if p["id"] in flags.get("projects", {}):
                p["specified"] = bool(flags["projects"][p["id"]])
        return True
    module = next((m for c in cur["courses"] for m in c["modules"] if m["id"] == module_id), None)
    if module is None:
        return False
    known = {lesson["id"] for lesson in module["lessons"]}
    for new in flags.get("newLessons", []):
        if new["id"] not in known:
            module["lessons"].append({"id": new["id"], "title": new["title"]})
    for lesson in module["lessons"]:
        f = flags.get("lessons", {}).get(lesson["id"])
        if f is not None:
            lesson.update(authored=True, exercises=f.get("exercises", []), quizzes=f.get("quizzes", []))
    if flags.get("assessment"):
        module["assessment"] = True
    return True


def main(module_id, flags_path):
    flags = json.loads(Path(flags_path).read_text(encoding="utf-8"))
    cur = copy.deepcopy(json.loads((CONTENT / "curriculum.json").read_text(encoding="utf-8")))
    if not apply(cur, module_id, flags):
        print(f"unknown module {module_id}")
        return 2
    if module_id == "PROJECTS":
        errs = validate.validate_curriculum(cur) + validate.validate_content(CONTENT, cur)
        problems = [e for e in errs if "project" in e.lower()]
        for p in problems:
            print(p)
        print(f"PROJECTS: {len(problems)} problem(s)")
        return 1 if problems else 0
    problems = [e for e in validate.validate_curriculum(cur) + validate.validate_content(CONTENT, cur) if module_id in e]
    for d in sorted(CONTENT.glob(f"exercises/{module_id}.*")):
        problems += [f"{d.name}: {p}" for p in check_exercises.check(d)]
    checked = 0
    for name, q in check_quizzes.output_quizzes(CONTENT, prefix=f"{module_id}."):
        probs, n, _ = check_quizzes.check_one(name, q)
        problems += probs
        checked += n
    for p in problems:
        print(p)
    print(f"{module_id}: {len(problems)} problem(s); {checked} output quiz(zes) executed")
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
