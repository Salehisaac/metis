"""Structural checks on ./ci.yml, a GitHub Actions workflow (parsed with PyYAML; nothing is run)."""
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).parent / "ci.yml"


def load():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and isinstance(data.get("jobs"), dict) and data["jobs"], "the workflow needs jobs:"
    return data


def triggers(data):
    """Event names under `on:`. PyYAML (YAML 1.1) loads the bare key `on` as True, so look for both."""
    on = data.get("on", data.get(True))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    if isinstance(on, dict):
        return set(on)
    return set()


def steps(job):
    return [s for s in job.get("steps") or [] if isinstance(s, dict)]


def index(job_steps, predicate):
    """Position of the first step matching predicate, or None."""
    return next((i for i, s in enumerate(job_steps) if predicate(s)), None)


def uses(name):
    return lambda s: str(s.get("uses", "")).split("@")[0] == name


def runs(text):
    return lambda s: text in str(s.get("run", ""))


def jobs_running(data, text):
    return [job for job in data["jobs"].values() if index(steps(job), runs(text)) is not None]


def test_runs_on_every_push():
    assert "push" in triggers(load()), "trigger the workflow on push"


def test_checks_out_the_code_before_anything_else():
    for job in load()["jobs"].values():
        st = steps(job)
        first = index(st, uses("actions/checkout"))
        assert first is not None, f"job without actions/checkout: {job}"
        assert first == 0, "check out the repository in the first step, or later steps see an empty directory"
        assert "@" in st[first]["uses"], "pin the action to a version: actions/checkout@vN"


def test_python_version_is_pinned_as_a_string():
    for job in load()["jobs"].values():
        st = steps(job)
        i = index(st, uses("actions/setup-python"))
        assert i is not None, "set up Python with actions/setup-python"
        assert "@" in st[i]["uses"], "pin the action to a version: actions/setup-python@vN"
        version = (st[i].get("with") or {}).get("python-version")
        assert isinstance(version, str), f"quote python-version: unquoted YAML numbers like 3.10 load as {version!r}"
        assert version == "3.12" or version.startswith("3.12."), f"use the project's Python, 3.12, got {version!r}"


def test_installs_from_requirements_with_pip_cache():
    for job in load()["jobs"].values():
        st = steps(job)
        setup = index(st, uses("actions/setup-python"))
        install = index(st, runs("-r requirements.txt"))
        assert install is not None and "pip install" in st[install]["run"], "install with pip install -r requirements.txt"
        assert setup is not None and setup < install, "set up Python before installing"
        assert (st[setup].get("with") or {}).get("cache") == "pip", "turn on setup-python's pip cache (cache: pip)"


def test_runs_ruff_lint_format_and_pytest_after_installing():
    data = load()
    for command in ("ruff check", "ruff format --check", "pytest"):
        jobs = jobs_running(data, command)
        assert jobs, f"no step runs `{command}`"
        for job in jobs:
            st = steps(job)
            install = index(st, runs("-r requirements.txt"))
            assert install is not None and install < index(st, runs(command)), f"install dependencies before `{command}`"


def test_each_check_is_its_own_step():
    for job in load()["jobs"].values():
        for s in steps(job):
            run = str(s.get("run", ""))
            found = [c for c in ("ruff check", "ruff format", "pytest") if c in run]
            assert len(found) <= 1, f"one check per step, so the log shows which one failed: {run!r}"
