"""Validate structured content. Stdlib only.

Usage: python tools/validate.py            (exit 1 and print errors if invalid)

The checks here are the data contract for content/*.json (schemaVersion 1).
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUSES = {"SKIP", "REVIEW", "LEARN", "DEEPEN", "APPLY"}
CONFIDENCE = {"High", "Medium", "Low", "Not assessed"}
COURSE_ID = re.compile(r"^[A-Z]+$")
PROJECT_ID = re.compile(r"^PRJ-\d{2}$")


def _req(obj, keys, where, errors):
    for k in keys:
        if k not in obj:
            errors.append(f"{where}: missing '{k}'")


def validate_curriculum(data):
    errors = []
    if data.get("schemaVersion") != 1:
        errors.append("curriculum: schemaVersion must be 1")
    seen = {}  # id -> kind

    def add(id_, kind, where):
        if id_ in seen:
            errors.append(f"{where}: duplicate id '{id_}'")
        seen[id_] = kind

    modules = []
    for c in data.get("courses", []):
        cw = f"course {c.get('id')}"
        _req(c, ["id", "title", "status", "reason", "modules"], cw, errors)
        if not COURSE_ID.match(str(c.get("id", ""))):
            errors.append(f"{cw}: bad id")
        if c.get("status") not in STATUSES:
            errors.append(f"{cw}: bad status '{c.get('status')}'")
        add(c.get("id"), "course", cw)
        for m in c.get("modules", []):
            mw = f"module {m.get('id')}"
            _req(m, ["id", "title", "status", "hours", "prereqs", "outcomes", "lessons"], mw, errors)
            if not re.match(rf"^{re.escape(str(c.get('id')))}\.M\d{{2}}$", str(m.get("id", ""))):
                errors.append(f"{mw}: id must be {c.get('id')}.Mnn")
            if m.get("status") not in STATUSES:
                errors.append(f"{mw}: bad status '{m.get('status')}'")
            if not isinstance(m.get("hours"), (int, float)) or m.get("hours", 0) <= 0:
                errors.append(f"{mw}: hours must be a positive number")
            if not m.get("outcomes"):
                errors.append(f"{mw}: needs at least one measurable outcome")
            add(m.get("id"), "module", mw)
            modules.append(m)
            for lesson in m.get("lessons", []):
                lw = f"lesson {lesson.get('id')}"
                _req(lesson, ["id", "title"], lw, errors)
                if not re.match(rf"^{re.escape(str(m.get('id')))}\.L\d{{2}}$", str(lesson.get("id", ""))):
                    errors.append(f"{lw}: id must be {m.get('id')}.Lnn")
                add(lesson.get("id"), "lesson", lw)

    for p in data.get("projects", []):
        pw = f"project {p.get('id')}"
        _req(p, ["id", "title", "after", "hours"], pw, errors)
        if not PROJECT_ID.match(str(p.get("id", ""))):
            errors.append(f"{pw}: bad id")
        add(p.get("id"), "project", pw)

    # Sequence: every module and project exactly once; prerequisites come earlier.
    seq = data.get("sequence", [])
    pos = {}
    for i, id_ in enumerate(seq):
        if id_ in pos:
            errors.append(f"sequence: '{id_}' appears twice")
        if seen.get(id_) not in ("module", "project"):
            errors.append(f"sequence: unknown module/project '{id_}'")
        pos[id_] = i
    for id_, kind in seen.items():
        if kind in ("module", "project") and id_ not in pos:
            errors.append(f"sequence: '{id_}' missing")
    deps = [(m["id"], m.get("prereqs", [])) for m in modules]
    deps += [(p["id"], p.get("after", [])) for p in data.get("projects", []) if "id" in p]
    for id_, reqs in deps:
        for r in reqs:
            if seen.get(r) != "module":
                errors.append(f"{id_}: prerequisite '{r}' is not a module")
            elif id_ in pos and r in pos and pos[r] >= pos[id_]:
                errors.append(f"{id_}: prerequisite '{r}' comes later in the sequence")
    return errors


def validate_assessments(data):
    errors = []
    if data.get("schemaVersion") != 1:
        errors.append("assessments: schemaVersion must be 1")
    for a in data.get("assessments", []):
        aw = f"assessment {a.get('id')}"
        _req(a, ["id", "date", "competencies"], aw, errors)
        for c in a.get("competencies", []):
            cw = f"{aw} / {c.get('name')}"
            for dim in "ABCD":
                v = c.get(dim, "missing")
                if v is not None and (not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 4):
                    errors.append(f"{cw}: {dim} must be 0-4 or null (not assessed)")
            if c.get("confidence") not in CONFIDENCE:
                errors.append(f"{cw}: bad confidence")
            scored = any(c.get(d) is not None for d in "ABCD")
            if scored == (c.get("confidence") == "Not assessed"):
                errors.append(f"{cw}: 'Not assessed' confidence must match all-null scores")
            if not c.get("evidence"):
                errors.append(f"{cw}: evidence required")
    return errors


def validate_profile(data):
    errors = [] if data.get("schemaVersion") == 1 else ["profile: schemaVersion must be 1"]
    if not str(data.get("background", "")).strip():
        errors.append("profile: background required")
    if "observed" in data and not (isinstance(data["observed"], list) and all(isinstance(x, str) and x.strip() for x in data["observed"])):
        errors.append("profile: 'observed' must be a list of strings (mentor observations, kept apart from stated preferences)")
    for k in ("goals", "preferences", "rules"):
        v = data.get(k)
        if not (isinstance(v, list) and v and all(isinstance(x, str) and x.strip() for x in v)):
            errors.append(f"profile: '{k}' must be a non-empty list of strings")
    return errors


CHECKS = {
    "content/curriculum.json": validate_curriculum,
    "content/learner/assessments.json": validate_assessments,
    "content/learner/profile.json": validate_profile,
}


# ---------------------------------------------------------------- authored content
# Lessons/assessments: Markdown with JSON front matter between "---" lines (same format parsed in site/assets/js/content.js).
DIFFICULTY = {"beginner", "intermediate", "advanced"}
QUIZ_TYPES = {"choice", "truefalse", "output", "explain"}
AUTO_GRADED = {"choice", "truefalse", "output"}  # explain is never auto-graded
FENCE = re.compile(r"^```(quiz|exercise)[ \t]*\n(.*?)\n```[ \t]*$", re.S | re.M)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_front_matter(text):
    """Return (meta: dict, body: str). Raises ValueError on a missing/invalid header."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError("missing front matter (file must start with '---')")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("unterminated front matter")
    meta = json.loads(text[4:end])
    if not isinstance(meta, dict):
        raise ValueError("front matter must be a JSON object")
    return meta, text[end + 5:]


def _str_list(v):
    return isinstance(v, list) and len(v) > 0 and all(isinstance(x, str) and x.strip() for x in v)


def validate_quiz(q, where):
    errors = []
    if not isinstance(q, dict):
        return [f"{where}: quiz must be a JSON object"]
    t = q.get("type")
    if t not in QUIZ_TYPES:
        return [f"{where}: quiz type must be one of {sorted(QUIZ_TYPES)}"]
    for k in ("id", "prompt", "explanation"):
        if not isinstance(q.get(k), str) or not q[k].strip():
            errors.append(f"{where}: quiz needs non-empty '{k}'")
    if not re.match(r"^[A-Za-z0-9_-]{1,40}$", str(q.get("id", ""))):
        errors.append(f"{where}: quiz id must match [A-Za-z0-9_-]{{1,40}} (it becomes part of progress event ids)")
    if "label" in q and not (isinstance(q["label"], str) and q["label"].strip()):
        errors.append(f"{where}: label must be a non-empty string (e.g. 'Debugging')")
    if t == "choice":
        opts = q.get("options")
        if not _str_list(opts) or len(opts) < 2:
            errors.append(f"{where}: choice quiz needs >= 2 options")
        elif not isinstance(q.get("answer"), int) or isinstance(q.get("answer"), bool) or not 0 <= q["answer"] < len(opts):
            errors.append(f"{where}: choice answer must be an option index")
    elif t == "truefalse" and not isinstance(q.get("answer"), bool):
        errors.append(f"{where}: truefalse answer must be true/false")
    elif t == "output":
        if not isinstance(q.get("answer"), str):
            errors.append(f"{where}: output answer must be a string")
        if "accept" in q and not _str_list(q["accept"]):
            errors.append(f"{where}: accept must be a list of strings")
    elif t == "explain" and not (isinstance(q.get("model"), str) and q["model"].strip()):
        errors.append(f"{where}: explain quiz needs a 'model' answer")
    return errors


def validate_body_blocks(body, where, allowed_exercises):
    errors, quiz_ids = [], set()
    for kind, raw in FENCE.findall(body):
        if kind == "exercise":
            if raw.strip() not in allowed_exercises:
                errors.append(f"{where}: exercise block '{raw.strip()}' not listed for this item")
            continue
        try:
            q = json.loads(raw)
        except ValueError as e:
            errors.append(f"{where}: quiz block is not valid JSON ({e})")
            continue
        errors += validate_quiz(q, where)
        if isinstance(q, dict) and q.get("id") in quiz_ids:
            errors.append(f"{where}: duplicate quiz id '{q.get('id')}'")
        quiz_ids.add(q.get("id") if isinstance(q, dict) else None)
    return errors


def validate_sources(sources, where):
    if not isinstance(sources, list) or not sources:
        return [f"{where}: at least one source required (spec §12)"]
    errors = []
    for i, s in enumerate(sources):
        sw = f"{where}: source {i + 1}"
        if not isinstance(s, dict):
            errors.append(f"{sw}: must be an object")
            continue
        if not str(s.get("url", "")).startswith("https://"):
            errors.append(f"{sw}: url must start with https://")
        if not DATE.match(str(s.get("verified", ""))):
            errors.append(f"{sw}: verified must be YYYY-MM-DD")
        for k in ("title", "version"):
            if not str(s.get(k, "")).strip():
                errors.append(f"{sw}: '{k}' required")
        if not _str_list(s.get("claims")):
            errors.append(f"{sw}: 'claims' must list the technical claims it supports")
    return errors


def validate_lesson(meta, body, lesson, index):
    w = f"lesson {lesson['id']}"
    errors = []
    if meta.get("id") != lesson["id"]:
        errors.append(f"{w}: front matter id must be '{lesson['id']}'")
    if meta.get("title") != lesson["title"]:
        errors.append(f"{w}: title must match curriculum.json")
    if meta.get("difficulty") not in DIFFICULTY:
        errors.append(f"{w}: difficulty must be one of {sorted(DIFFICULTY)}")
    if not isinstance(meta.get("minutes"), int) or isinstance(meta.get("minutes"), bool) or meta["minutes"] <= 0:
        errors.append(f"{w}: minutes must be a positive integer")
    prereqs = meta.get("prerequisites")
    if not isinstance(prereqs, list) or any(p not in index for p in prereqs):
        errors.append(f"{w}: prerequisites must be a list of existing curriculum ids")
    for k in ("objectives", "applications"):
        if not _str_list(meta.get(k)):
            errors.append(f"{w}: '{k}' must be a non-empty list of strings")
    if not str(meta.get("why", "")).strip():
        errors.append(f"{w}: 'why' required")
    if meta.get("exercises", []) != lesson.get("exercises", []):
        errors.append(f"{w}: exercises must match curriculum.json")
    errors += validate_sources(meta.get("sources"), w)
    errors += validate_body_blocks(body, w, set(lesson.get("exercises", [])))
    # Progress derivation reads auto-graded quiz ids from curriculum.json (no fetching lesson bodies), so they must agree.
    auto = []
    for kind, raw in FENCE.findall(body):
        try:
            q = json.loads(raw) if kind == "quiz" else None
        except ValueError:
            continue
        if isinstance(q, dict) and q.get("type") in AUTO_GRADED:
            auto.append(q.get("id"))
    if lesson.get("quizzes", []) != auto:
        errors.append(f"{w}: curriculum.json quizzes {lesson.get('quizzes', [])} must list the auto-graded quiz ids in order {auto}")
    return errors


EXERCISE_TEXT = ("id", "lesson", "title", "problem", "contract", "expectedBehavior")
EXERCISE_LISTS = ("requirements", "edgeCases", "evaluation", "tests")  # tests: expected pytest test names


def validate_exercise(ex_dir, ex_id, lesson_id):
    w = f"exercise {ex_id}"
    try:
        ex = json.loads((ex_dir / "exercise.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"{w}: exercise.json: {e}"]
    errors = [f"{w}: '{k}' required" for k in EXERCISE_TEXT if not str(ex.get(k, "")).strip()]
    errors += [f"{w}: '{k}' must be a non-empty list" for k in EXERCISE_LISTS if not _str_list(ex.get(k))]
    if ex.get("id") != ex_id or ex.get("lesson") != lesson_id:
        errors.append(f"{w}: id/lesson must be '{ex_id}'/'{lesson_id}'")
    if not _str_list(ex.get("hints")) or len(ex["hints"]) != 3:
        errors.append(f"{w}: exactly 3 hints required (conceptual, specific, implementation)")
    starter = ex_dir / "starter"
    if not any(starter.glob("test_*.py")):
        errors.append(f"{w}: starter/ needs at least one test_*.py")
    if not (ex_dir / "solution" / "SOLUTION.md").is_file():
        errors.append(f"{w}: solution/SOLUTION.md required (reference solution, kept separate)")
    return errors


def validate_content(content, curriculum):
    """Authored files <-> curriculum flags, both directions; then each file's contract."""
    errors = []
    index = {}
    for c in curriculum.get("courses", []):
        index[c["id"]] = c
        for m in c.get("modules", []):
            index[m["id"]] = m
            for lesson in m.get("lessons", []):
                index[lesson["id"]] = lesson
    lessons = [x for x in index.values() if re.match(r"^[A-Z]+\.M\d{2}\.L\d{2}$", x.get("id", ""))]
    modules = [x for x in index.values() if re.match(r"^[A-Z]+\.M\d{2}$", x.get("id", ""))]

    def present(pattern):
        return {p.name for p in content.glob(pattern)}

    lesson_files = present("lessons/*.md")
    for lesson in lessons:
        name = f"{lesson['id']}.md"
        if bool(lesson.get("authored")) != (name in lesson_files):
            errors.append(f"lesson {lesson['id']}: 'authored' flag and lessons/{name} disagree")
        if name not in lesson_files:
            if lesson.get("exercises") or lesson.get("quizzes"):
                errors.append(f"lesson {lesson['id']}: exercises/quizzes listed but lesson not authored")
            continue
        try:
            meta, body = parse_front_matter((content / "lessons" / name).read_text(encoding="utf-8"))
        except ValueError as e:
            errors.append(f"lessons/{name}: {e}")
            continue
        errors += validate_lesson(meta, body, lesson, index)
        for ex_id in lesson.get("exercises", []):
            if not re.match(rf"^{re.escape(lesson['id'])}\.E\d+$", ex_id):
                errors.append(f"lesson {lesson['id']}: exercise id '{ex_id}' must be {lesson['id']}.En")
            elif not (content / "exercises" / ex_id).is_dir():
                errors.append(f"lesson {lesson['id']}: exercises/{ex_id}/ missing")
            else:
                errors += validate_exercise(content / "exercises" / ex_id, ex_id, lesson["id"])
    known = {f"{x['id']}.md" for x in lessons}
    errors += [f"lessons/{n}: not a curriculum lesson" for n in sorted(lesson_files - known)]
    listed = {e for x in lessons for e in x.get("exercises", [])}
    errors += [f"exercises/{n}/: not listed by any lesson" for n in sorted(present("exercises/*") - listed)]

    assessment_files = present("assessments/*.md")
    for m in modules:
        name = f"{m['id']}.A.md"
        if bool(m.get("assessment")) != (name in assessment_files):
            errors.append(f"module {m['id']}: 'assessment' flag and assessments/{name} disagree")
        elif name in assessment_files:
            try:
                meta, body = parse_front_matter((content / "assessments" / name).read_text(encoding="utf-8"))
            except ValueError as e:
                errors.append(f"assessments/{name}: {e}")
                continue
            if meta.get("id") != f"{m['id']}.A" or meta.get("module") != m["id"]:
                errors.append(f"assessments/{name}: id/module must be '{m['id']}.A'/'{m['id']}'")
            errors += validate_body_blocks(body, f"assessment {m['id']}.A", set())
    errors += [f"assessments/{n}: unknown module" for n in sorted(assessment_files - {f"{m['id']}.A.md" for m in modules})]

    project_files = present("projects/*.md")
    for p in curriculum.get("projects", []):
        if bool(p.get("specified")) != (f"{p['id']}.md" in project_files):
            errors.append(f"project {p['id']}: 'specified' flag and projects/{p['id']}.md disagree")
    return errors


def main(content=ROOT / "content"):
    errors = []
    loaded = {}
    for rel, check in CHECKS.items():
        try:
            data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            errors.append(f"{rel}: {e}")
            continue
        loaded[rel] = data
        errors += [f"{rel}: {e}" for e in check(data)]
    if "content/curriculum.json" in loaded:
        errors += validate_content(content, loaded["content/curriculum.json"])
    for e in errors:
        print(e)
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
