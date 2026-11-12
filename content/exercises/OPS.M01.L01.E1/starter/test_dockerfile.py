"""Static checks on ./Dockerfile (Docker isn't needed: the file is parsed, not built)."""
import json
import re
from pathlib import Path

DOCKERFILE = Path(__file__).parent / "Dockerfile"
SECRET_NAME = re.compile(r"SECRET|PASSWORD|PASSWD|TOKEN|API_KEY|PRIVATE_KEY", re.I)


def instructions():
    """-> [(INSTRUCTION, args)]: comments and blank lines dropped, '\\' continuations joined."""
    out, buf = [], ""
    for raw in DOCKERFILE.read_text(encoding="utf-8").splitlines():
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


def final_stage():
    """Instructions from the last FROM on (the image that actually ships)."""
    ins = instructions()
    last_from = max(i for i, (word, _) in enumerate(ins) if word == "FROM")
    return ins[last_from:]


def env_names(args):
    """Variable names set by one ENV/ARG line: 'A=1 B=2', 'A 1' or 'A'."""
    if "=" not in args:
        return [args.split()[0]] if args else []
    return [part.split("=", 1)[0] for part in args.split() if "=" in part]


def test_base_image_is_a_pinned_python_slim():
    args = [a for a in final_stage()[0][1].split() if not a.startswith("--")]
    image = args[0]
    name, _, tag = image.partition(":")
    assert name == "python", f"base image should be python:..., got {image}"
    assert tag and tag != "latest", f"pin a version tag, not {image!r}"
    assert re.match(r"^\d+\.\d+", tag), f"the tag should start with a Python version like 3.12, got {tag!r}"
    assert "slim" in tag, f"use a slim variant, got {tag!r}"


def test_runs_as_a_non_root_user_that_exists():
    stage = final_stage()
    users = [i for i, (word, _) in enumerate(stage) if word == "USER"]
    assert users, "add a USER instruction so the app doesn't run as root"
    user = stage[users[-1]][1].split(":")[0]
    assert user not in ("root", "0"), f"USER {user} is still root"
    if not user.isdigit():
        created = [args for word, args in stage[: users[-1]] if word == "RUN" and re.search(r"useradd|adduser", args)]
        assert any(re.search(rf"\b{re.escape(user)}\b", args) for args in created), (
            f"create the user {user!r} in a RUN (useradd) before USER {user}"
        )


def test_cmd_is_exec_form_uvicorn_on_all_interfaces():
    cmds = [args for word, args in final_stage() if word == "CMD"]
    assert cmds, "CMD missing"
    try:
        cmd = json.loads(cmds[-1])
    except json.JSONDecodeError:
        raise AssertionError(f"CMD is in shell form: {cmds[-1]!r}. Use a JSON array with double quotes.") from None
    assert isinstance(cmd, list) and all(isinstance(x, str) for x in cmd), "CMD must be a JSON array of strings"
    assert "uvicorn" in cmd, f"run uvicorn, got {cmd}"
    assert "app.main:app" in cmd, f"serve app.main:app, got {cmd}"
    assert "--host" in cmd and cmd[cmd.index("--host") + 1] == "0.0.0.0", "uvicorn must listen on 0.0.0.0"
    assert "--port" in cmd and cmd[cmd.index("--port") + 1] == "8000", "keep the app on port 8000"


def test_no_secrets_baked_into_the_image():
    for word, args in instructions():
        if word in ("ENV", "ARG"):
            bad = [n for n in env_names(args) if SECRET_NAME.search(n)]
            assert not bad, f"{word} {args!r} bakes a secret into the image; pass it at run time instead"
