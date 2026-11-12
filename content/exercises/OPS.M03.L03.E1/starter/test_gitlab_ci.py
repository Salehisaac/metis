"""Structural checks on ./.gitlab-ci.yml (parsed with PyYAML; no runner needed)."""
import re
from pathlib import Path

import yaml

PIPELINE = Path(__file__).parent / ".gitlab-ci.yml"
GLOBAL_KEYS = {"default", "include", "stages", "variables", "workflow", "image", "services", "cache",
               "before_script", "after_script", "spec"}
CHECKS = ("ruff check", "ruff format --check", "pytest")
SECRET_KEY = re.compile(r"SECRET|PASSWORD|PASSWD|TOKEN|API_KEY|PRIVATE_KEY", re.I)


def load():
    data = yaml.safe_load(PIPELINE.read_text(encoding="utf-8"))
    assert isinstance(data, dict), ".gitlab-ci.yml must be a YAML mapping"
    return data


def jobs(data):
    """Job name -> job mapping. Hidden jobs (.name) are templates, not jobs."""
    found = {k: v for k, v in data.items() if k not in GLOBAL_KEYS and not str(k).startswith(".") and isinstance(v, dict)}
    assert found, "no jobs found"
    return found


def setting(data, job, key):
    """A job's own keyword wins; otherwise default:, otherwise the (deprecated) top-level keyword."""
    for source in (job, data.get("default") or {}, data):
        if key in source:
            return source[key]
    return None


def commands(data, job):
    """before_script + script lines, in the order the runner executes them."""
    return [str(c) for c in (setting(data, job, "before_script") or []) + (job.get("script") or [])]


def check_jobs(data):
    return {name: job for name, job in jobs(data).items() if any(c in cmd for cmd in commands(data, job) for c in CHECKS)}


def test_image_is_a_pinned_python_312():
    data = load()
    for name, job in check_jobs(data).items():
        image = setting(data, job, "image")
        ref = image.get("name") if isinstance(image, dict) else image
        assert isinstance(ref, str), f"{name}: set an image (in default: or the job)"
        repo, _, tag = ref.partition(":")
        assert repo == "python" and tag.startswith("3.12"), f"{name}: use python:3.12... (pinned), got {ref!r}"


def test_no_secrets_in_the_file():
    data = load()
    sources = [("variables", data.get("variables") or {})]
    sources += [(f"{n}.variables", j.get("variables") or {}) for n, j in jobs(data).items()]
    for where, variables in sources:
        bad = [k for k in variables if SECRET_KEY.search(str(k))]
        assert not bad, f"{where} defines {bad}: secrets belong in masked CI/CD variables in the project settings"


def test_pip_downloads_are_cached_per_requirements_file():
    data = load()
    for name, job in check_jobs(data).items():
        variables = {**(data.get("variables") or {}), **(job.get("variables") or {})}
        pip_dir = str(variables.get("PIP_CACHE_DIR", ""))
        m = re.match(r"^\$\{?CI_PROJECT_DIR\}?/(.+?)/?$", pip_dir)
        assert m, f"{name}: set PIP_CACHE_DIR to a folder inside $CI_PROJECT_DIR (caches only work inside the project)"
        caches = setting(data, job, "cache") or []
        caches = caches if isinstance(caches, list) else [caches]
        ok = [c for c in caches if isinstance(c, dict)
              and m.group(1) in [str(p).rstrip("/") for p in c.get("paths") or []]
              and "requirements.txt" in ((c.get("key") or {}).get("files") or [] if isinstance(c.get("key"), dict) else [])]
        assert ok, f"{name}: cache paths must include {m.group(1)!r} with key: files: [requirements.txt]"


def test_installs_requirements_before_any_check():
    data = load()
    for name, job in check_jobs(data).items():
        cmds = commands(data, job)
        installs = [i for i, c in enumerate(cmds) if "pip install" in c and "-r requirements.txt" in c]
        first_check = min(i for i, c in enumerate(cmds) if any(x in c for x in CHECKS))
        assert installs and installs[0] < first_check, f"{name}: pip install -r requirements.txt must come before the checks"


def test_runs_ruff_lint_format_and_pytest():
    data = load()
    all_cmds = [c for job in jobs(data).values() for c in commands(data, job)]
    for check in CHECKS:
        assert any(check in c for c in all_cmds), f"no job runs `{check}`"


def test_each_check_is_its_own_script_line():
    data = load()
    for name, job in jobs(data).items():
        for cmd in commands(data, job):
            found = [c for c in CHECKS if c in cmd]
            assert len(found) <= 1, f"{name}: {cmd!r} combines checks; GitLab reports only the last command's result"
