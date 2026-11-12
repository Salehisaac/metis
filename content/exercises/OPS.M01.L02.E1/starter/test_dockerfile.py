"""Static checks on ./Dockerfile and ./.dockerignore (parsed, not built: Docker isn't needed)."""
import json
import re
from fnmatch import fnmatch
from pathlib import Path

HERE = Path(__file__).parent


def instructions():
    """-> [(INSTRUCTION, args)]: comments and blank lines dropped, '\\' continuations joined."""
    out, buf = [], ""
    for raw in (HERE / "Dockerfile").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        word, _, rest = (buf + line).partition(" ")
        out.append((word.upper(), rest.strip()))
        buf = ""
    return out


def final_stage(ins):
    last_from = max(i for i, (word, _) in enumerate(ins) if word == "FROM")
    return ins[last_from:]


def copy_sources(args):
    """Source paths of a COPY line (flags like --chown dropped, destination dropped)."""
    parts = [p for p in args.split() if not p.startswith("--")]
    return parts[:-1]


def ignore_patterns():
    path = HERE / ".dockerignore"
    assert path.is_file(), ".dockerignore missing"
    lines = [x.strip() for x in path.read_text(encoding="utf-8").splitlines()]
    pats = [x for x in lines if x and not x.startswith(("#", "!"))]
    return [p.removeprefix("**/").strip("/") for p in pats]


def ignored(name, pats):
    return any(fnmatch(name, p) for p in pats)


def test_dependencies_install_before_the_source_is_copied():
    ins = instructions()
    req_copy = [i for i, (w, a) in enumerate(ins) if w == "COPY" and "--from" not in a
                and copy_sources(a) and all("requirements" in s for s in copy_sources(a))]
    pip = [i for i, (w, a) in enumerate(ins) if w == "RUN" and "pip install" in a and "requirements" in a]
    src_copy = [i for i, (w, a) in enumerate(ins) if w == "COPY" and "--from" not in a
                and any("requirements" not in s for s in copy_sources(a))]
    assert req_copy, "COPY requirements.txt on its own first"
    assert pip, "RUN pip install -r ...requirements.txt is missing"
    assert src_copy, "the app source is never copied"
    assert req_copy[0] < pip[0] < src_copy[0], (
        "order must be: COPY requirements -> RUN pip install -> COPY source, so code edits keep the install layer cached"
    )


def test_pip_install_keeps_no_download_cache():
    pip = [a for w, a in instructions() if w == "RUN" and "pip install" in a]
    assert pip and all("--no-cache-dir" in a for a in pip), "pip's download cache is dead weight in an image: --no-cache-dir"


def test_healthcheck_probes_the_health_endpoint():
    ins = instructions()
    stage = final_stage(ins)
    checks = [a for w, a in stage if w == "HEALTHCHECK"]
    assert checks, "add a HEALTHCHECK to the final stage"
    m = re.match(r"^((?:--\S+\s+)*)CMD\s+(.*)$", checks[-1], re.S)
    assert m, f"HEALTHCHECK must be [OPTIONS] CMD ..., got {checks[-1]!r}"
    try:
        cmd = json.loads(m.group(2))
    except json.JSONDecodeError:
        raise AssertionError("write the HEALTHCHECK command in exec form (a JSON array)") from None
    text = " ".join(cmd)
    assert "/health" in text and "8000" in text, f"probe http://localhost:8000/health, got {cmd}"
    tool = cmd[0]
    if tool in ("curl", "wget"):
        installs = [a for w, a in stage if w == "RUN" and "install" in a and tool in a]
        assert installs, f"{tool} isn't something the slim image promises; install it or probe with python"


def test_dockerignore_keeps_junk_and_secrets_out():
    pats = ignore_patterns()
    for name in (".git", ".venv", "__pycache__", ".env"):
        assert ignored(name, pats), f".dockerignore should exclude {name}"
    for name in ("requirements.txt", "app", "Dockerfile"):
        assert not ignored(name, pats), f".dockerignore must not exclude {name}"


def test_last_lessons_rules_still_hold():
    stage = final_stage(instructions())
    users = [a for w, a in stage if w == "USER"]
    assert users and users[-1].split(":")[0] not in ("root", "0"), "still run as a non-root USER"
    cmds = [a for w, a in stage if w == "CMD"]
    assert cmds and cmds[-1].startswith("["), "keep the exec-form CMD"
