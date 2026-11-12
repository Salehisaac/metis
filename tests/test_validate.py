import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import validate  # noqa: E402

CURRICULUM = json.loads((ROOT / "content/curriculum.json").read_text())
ASSESSMENTS = json.loads((ROOT / "content/learner/assessments.json").read_text())


def test_real_content_is_valid():
    assert validate.main() == 0


def test_duplicate_id_rejected():
    d = copy.deepcopy(CURRICULUM)
    d["courses"][0]["modules"][0]["lessons"][1]["id"] = "PY.M01.L01"  # well-formed id, but a duplicate
    assert any("duplicate id 'PY.M01.L01'" in e for e in validate.validate_curriculum(d))


def test_prereq_after_dependent_rejected():
    d = copy.deepcopy(CURRICULUM)
    d["courses"][0]["modules"][0]["prereqs"] = ["PY.M02"]
    assert any("comes later" in e for e in validate.validate_curriculum(d))


def test_unknown_prereq_rejected():
    d = copy.deepcopy(CURRICULUM)
    d["courses"][0]["modules"][0]["prereqs"] = ["NOPE.M01"]
    assert any("not a module" in e for e in validate.validate_curriculum(d))


def test_missing_from_sequence_rejected():
    d = copy.deepcopy(CURRICULUM)
    d["sequence"].remove("PRJ-03")
    assert any("'PRJ-03' missing" in e for e in validate.validate_curriculum(d))


def test_bad_status_rejected():
    d = copy.deepcopy(CURRICULUM)
    d["courses"][1]["modules"][0]["status"] = "MASTERED"
    assert any("bad status" in e for e in validate.validate_curriculum(d))


def test_score_out_of_range_rejected():
    d = copy.deepcopy(ASSESSMENTS)
    d["assessments"][0]["competencies"][0]["A"] = 5
    assert any("0-4 or null" in e for e in validate.validate_assessments(d))


def test_bool_score_rejected():
    d = copy.deepcopy(ASSESSMENTS)
    d["assessments"][0]["competencies"][0]["A"] = True
    assert validate.validate_assessments(d)


def test_profile_contract():
    good = json.loads((ROOT / "content/learner/profile.json").read_text())
    assert validate.validate_profile(good) == []
    assert validate.validate_profile({**good, "rules": []})
    assert validate.validate_profile({**good, "background": " "})


def test_not_assessed_must_have_null_scores():
    d = copy.deepcopy(ASSESSMENTS)
    d["assessments"][0]["competencies"][0]["confidence"] = "Not assessed"
    assert any("Not assessed" in e for e in validate.validate_assessments(d))
