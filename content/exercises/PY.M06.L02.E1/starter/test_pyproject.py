"""Checks pyproject.toml with tomllib (the stdlib TOML parser). Nothing gets installed."""

import ast
import tomllib
from pathlib import Path

HERE = Path(__file__).parent


def load():
    with open(HERE / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def names(requirements):
    """'httpx>=0.27' -> 'httpx' (good enough for simple requirement strings)."""
    out = []
    for req in requirements:
        for sep in "<>=!~[; ":
            req = req.split(sep)[0]
        out.append(req.lower())
    return out


def test_project_identity_unchanged():
    project = load()["project"]
    assert project["name"] == "pingwatch"
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.12"
    assert load()["build-system"]["build-backend"] == "setuptools.build_meta"


def test_dependencies_belong_to_project():
    doc = load()
    deps = doc["project"].get("dependencies")
    assert isinstance(deps, list), (
        "[project] has no `dependencies` list. Which table is it really in?"
    )
    for name, target in doc["project"].get("scripts", {}).items():
        assert isinstance(target, str), (
            f"[project.scripts] entry {name!r} is not a 'module:function' string"
        )


def test_httpx_is_a_lower_bound_not_a_pin():
    deps = load()["project"].get("dependencies", [])
    httpx = [d for d in deps if names([d]) == ["httpx"]]
    assert httpx, f"httpx missing from [project] dependencies: {deps}"
    assert ">=" in httpx[0], f"{httpx[0]!r}: give a minimum version with >="
    assert "==" not in httpx[0], (
        f"{httpx[0]!r}: exact pins belong in requirements files, not in dependencies"
    )


def test_pytest_is_a_dev_extra():
    project = load()["project"]
    assert "pytest" not in names(project.get("dependencies", [])), (
        "users of pingwatch don't need pytest"
    )
    dev = project.get("optional-dependencies", {}).get("dev", [])
    assert "pytest" in names(dev), f"dev extra is {dev}"
    assert "ruff" in names(dev), "keep ruff in the dev extra"


def test_console_script_points_at_a_real_function():
    scripts = load()["project"].get("scripts", {})
    assert "pingwatch" in scripts, (
        f"no pingwatch command in [project.scripts]: {scripts}"
    )
    module, _, func = scripts["pingwatch"].partition(":")
    # With the src layout, import names start inside src/: package 'x' lives in src/x/.
    path = HERE / "src" / Path(*module.split(".")).with_suffix(".py")
    assert path.is_file(), (
        f"{module!r} would be imported from {path.relative_to(HERE)}, which doesn't exist"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defined = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert func in defined, f"{path.name} defines {defined}, not {func!r}"
