"""Content contracts, scaffolder and exercise checker, exercised on tests/fixtures/content."""

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "content"
sys.path.insert(0, str(ROOT / "tools"))
import check_exercises  # noqa: E402
import check_quizzes  # noqa: E402
import scaffold  # noqa: E402
import validate  # noqa: E402

REAL = json.loads((ROOT / "content" / "curriculum.json").read_text())


def fixture_curriculum():
    """Real curriculum, with the flags the fixture content claims."""
    cur = copy.deepcopy(REAL)
    for c in cur["courses"]:  # start from "nothing authored", then claim exactly what the fixtures contain
        for m in c["modules"]:
            m.pop("assessment", None)
            for lesson in m["lessons"]:
                for k in ("authored", "exercises", "quizzes"):
                    lesson.pop(k, None)
    py = cur["courses"][0]["modules"][0]
    py["lessons"][0]["authored"] = True
    py["lessons"][0]["exercises"] = ["PY.M01.L01.E1"]
    py["lessons"][0]["quizzes"] = ["q1", "q2", "q3"]
    py["assessment"] = True
    for p in cur["projects"]:
        p["specified"] = False
    return cur


@pytest.fixture
def content(tmp_path):
    """Writable copy of the fixture content tree."""
    dest = tmp_path / "content"
    shutil.copytree(FIX, dest)
    return dest


def errors(content_dir, cur=None):
    return validate.validate_content(content_dir, cur or fixture_curriculum())


def edit_lesson(content_dir, fn):
    p = content_dir / "lessons" / "PY.M01.L01.md"
    meta, body = validate.parse_front_matter(p.read_text())
    meta, body = fn(meta, body)
    p.write_text("---\n" + json.dumps(meta) + "\n---\n" + body)


def test_fixture_content_is_valid():
    assert errors(FIX) == []


def test_real_content_is_valid():
    assert validate.main() == 0


def test_real_exercises_pass_the_checker():
    assert check_exercises.main() == 0


def test_real_output_quiz_answers_match_running_the_code():
    problems, checked, _ = check_quizzes.check(ROOT / "content")
    assert problems == [] and checked >= 1


def test_quiz_checker_catches_a_wrong_answer(content):
    edit_lesson(content, lambda m, b: (m, b.replace('"answer": "[1, 2, 3]"', '"answer": "[1, 2]"')))
    problems, _, _ = check_quizzes.check(content)
    assert any("q3" in p for p in problems)


def test_flag_without_file_and_file_without_flag(content):
    cur = fixture_curriculum()
    cur["courses"][0]["modules"][0]["lessons"][1]["authored"] = True  # PY.M01.L02 has no file
    assert any("PY.M01.L02" in e and "disagree" in e for e in errors(content, cur))
    cur = fixture_curriculum()
    cur["courses"][0]["modules"][0]["lessons"][0]["authored"] = False
    cur["courses"][0]["modules"][0]["lessons"][0]["exercises"] = []
    assert any("PY.M01.L01" in e and "disagree" in e for e in errors(content, cur))


def test_missing_sources_rejected(content):
    edit_lesson(content, lambda m, b: ({**m, "sources": []}, b))
    assert any("source" in e for e in errors(content))


def test_source_needs_https_and_claims(content):
    def bad(m, b):
        m["sources"][0]["url"] = "http://example.com"
        m["sources"][0]["claims"] = []
        return m, b
    edit_lesson(content, bad)
    errs = errors(content)
    assert any("https://" in e for e in errs) and any("claims" in e for e in errs)


def test_title_must_match_curriculum(content):
    edit_lesson(content, lambda m, b: ({**m, "title": "Something else"}, b))
    assert any("title must match" in e for e in errors(content))


def test_invalid_quiz_json_rejected(content):
    edit_lesson(content, lambda m, b: (m, b + '\n```quiz\n{ "id": "x", \n```\n'))
    assert any("not valid JSON" in e for e in errors(content))


def test_quiz_contract(content):
    bad = '{"id": "z", "type": "choice", "prompt": "p", "options": ["a"], "answer": 3, "explanation": "e"}'
    edit_lesson(content, lambda m, b: (m, b + f"\n```quiz\n{bad}\n```\n"))
    assert any("2 options" in e for e in errors(content))


def test_duplicate_quiz_id(content):
    dup = '{"id": "q1", "type": "truefalse", "prompt": "p", "answer": true, "explanation": "e"}'
    edit_lesson(content, lambda m, b: (m, b + f"\n```quiz\n{dup}\n```\n"))
    assert any("duplicate quiz id 'q1'" in e for e in errors(content))


def test_unlisted_exercise_block(content):
    edit_lesson(content, lambda m, b: (m, b + "\n```exercise\nPY.M01.L01.E9\n```\n"))
    assert any("not listed" in e for e in errors(content))


def test_curriculum_quiz_ids_must_match_body(content):
    cur = fixture_curriculum()
    cur["courses"][0]["modules"][0]["lessons"][0]["quizzes"] = ["q1", "q2"]  # q3 missing
    assert any("auto-graded quiz ids" in e for e in errors(content, cur))
    cur["courses"][0]["modules"][0]["lessons"][0]["quizzes"] = ["q1", "q2", "q3", "q4"]  # q4 is explain: not auto-graded
    assert any("auto-graded quiz ids" in e for e in errors(content, cur))


def test_exercise_needs_three_hints(content):
    p = content / "exercises" / "PY.M01.L01.E1" / "exercise.json"
    ex = json.loads(p.read_text())
    ex["hints"] = ex["hints"][:2]
    p.write_text(json.dumps(ex))
    assert any("exactly 3 hints" in e for e in errors(content))


def test_exercise_needs_separate_solution(content):
    (content / "exercises" / "PY.M01.L01.E1" / "solution" / "SOLUTION.md").unlink()
    assert any("SOLUTION.md" in e for e in errors(content))


def test_front_matter_parse_errors():
    with pytest.raises(ValueError):
        validate.parse_front_matter("no header")
    with pytest.raises(ValueError):
        validate.parse_front_matter("---\n{}\n")
    with pytest.raises(ValueError):
        validate.parse_front_matter("---\n[1]\n---\nbody")
    assert validate.parse_front_matter('---\r\n{"a": 1}\r\n---\r\nbody') == ({"a": 1}, "body")


def test_scaffold_copies_starter_not_solution_and_refuses_overwrite(tmp_path):
    dest = scaffold.scaffold("PY.M01.L01.E1", content=FIX, workspace=tmp_path)
    names = {p.name for p in dest.iterdir()}
    assert names == {"words.py", "test_words.py", "pytest.ini"}
    assert "NotImplementedError" in (dest / "words.py").read_text()  # starter, not the solution
    assert "junit_suite_name = PY.M01.L01.E1" in (dest / "pytest.ini").read_text()
    (dest / "words.py").write_text("# learner work")
    with pytest.raises(FileExistsError):
        scaffold.scaffold("PY.M01.L01.E1", content=FIX, workspace=tmp_path)
    assert (dest / "words.py").read_text() == "# learner work"


def test_scaffold_rejects_bad_ids(tmp_path):
    for bad in ("../etc", "PY.M01.L01", "PY.M01.L01.E1/../../x"):
        with pytest.raises(ValueError):
            scaffold.scaffold(bad, content=FIX, workspace=tmp_path)


def test_checker_passes_fixture():
    assert check_exercises.check(FIX / "exercises" / "PY.M01.L01.E1") == []


def test_checker_catches_tests_that_pass_on_starter(content):
    ex = content / "exercises" / "PY.M01.L01.E1"
    shutil.copy(ex / "solution" / "words.py", ex / "starter" / "words.py")  # starter already solved
    assert any("starter should fail" in p for p in check_exercises.check(ex))


def test_checker_catches_import_errors_on_starter(content):
    ex = content / "exercises" / "PY.M01.L01.E1"
    (ex / "starter" / "words.py").unlink()  # tests can't even import -> error, wrong kind of failure
    assert any("starter should fail" in p for p in check_exercises.check(ex))


def test_exercise_needs_expected_test_names(content):
    p = content / "exercises" / "PY.M01.L01.E1" / "exercise.json"
    ex = json.loads(p.read_text())
    del ex["tests"]
    p.write_text(json.dumps(ex))
    assert any("'tests'" in e for e in errors(content))


def test_checker_catches_test_name_mismatch(content):
    ex = content / "exercises" / "PY.M01.L01.E1"
    data = json.loads((ex / "exercise.json").read_text())
    data["tests"] = ["test_example", "test_renamed"]
    (ex / "exercise.json").write_text(json.dumps(data))
    assert any("test names" in p for p in check_exercises.check(ex))


def test_leak_check_flags_a_lesson_that_prints_the_solution(content):
    ex = content / "exercises" / "PY.M01.L01.E1"
    assert check_exercises.leaked_lines(ex) == []
    solution = (ex / "solution" / "words.py").read_text()
    edit_lesson(content, lambda m, b: (m, b + "\n```python\n" + solution + "```\n"))
    leaks = check_exercises.leaked_lines(ex)
    assert len(leaks) >= check_exercises.LEAK_LIMIT, leaks


def test_checker_catches_broken_solution(content):
    ex = content / "exercises" / "PY.M01.L01.E1"
    (ex / "solution" / "words.py").write_text("def count_words(text):\n    return {}\n")
    assert any("reference solution" in p for p in check_exercises.check(ex))
