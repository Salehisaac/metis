---
{
  "id": "PY.M06.L02",
  "title": "pyproject.toml and project layout",
  "difficulty": "intermediate",
  "minutes": 40,
  "prerequisites": ["PY.M01.L02", "PY.M06.L01"],
  "objectives": [
    "Write a pyproject.toml with [build-system], [project] (name, version, requires-python, dependencies), an optional dev extra and a [project.scripts] command",
    "Read TOML correctly: say which table a key belongs to",
    "Choose between the src layout and the flat layout, and explain what the src layout prevents",
    "Install a project in editable mode and predict when you must reinstall",
    "Decide what goes in [project] dependencies (minimum versions) and what goes in a pinned requirements file"
  ],
  "why": "Every real Python service, and every FastAPI template you'll meet, starts with a pyproject.toml. It is to Python what go.mod is to Go: the project's name, Python version, dependencies, commands and tool settings in one file. Getting it right means `pip install -e .` just works and imports behave the same in your shell, in tests and in Docker.",
  "applications": [
    "Turning a folder of scripts into an installable project with its own CLI command",
    "Declaring runtime vs development dependencies for a FastAPI service",
    "One place for tool configuration (pytest, Ruff) instead of many dotfiles"
  ],
  "exercises": ["PY.M06.L02.E1"],
  "sources": [
    {
      "title": "Writing your pyproject.toml (Python Packaging User Guide)",
      "url": "https://packaging.python.org/en/latest/guides/writing-pyproject-toml/",
      "version": "PyPA guide, latest (fetched 2026-11-12; page shows no version)",
      "verified": "2026-11-12",
      "claims": [
        "[build-system] should always be present; requires lists build dependencies and build-backend names the backend (setuptools example: setuptools >= 77.0.3, setuptools.build_meta)",
        "[project] name is required; version is required but may be dynamic",
        "dependencies, requires-python and [project.optional-dependencies] (extras)",
        "[project.scripts] installs a command",
        "[tool] has tool-specific subtables"
      ]
    },
    {
      "title": "Packaging Python Projects (tutorial)",
      "url": "https://packaging.python.org/en/latest/tutorials/packaging-projects/",
      "version": "PyPA tutorial, latest (fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Example src layout: src/<package>/__init__.py", "The tutorial uses Hatchling but works the same with setuptools, Flit, PDM", "name is the distribution name"]
    },
    {
      "title": "src layout vs flat layout",
      "url": "https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/",
      "version": "PyPA discussion, latest (fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["The src layout requires installing the project to run its code", "It prevents accidental use of the in-development copy, because the current directory is first on the import path", "Editable installs then expose only the package, not config files"]
    },
    {
      "title": "pip: Local project installs (editable installs)",
      "url": "https://pip.pypa.io/en/stable/topics/local-project-installs/",
      "version": "pip docs v26.3; behaviour verified locally with pip 24.0 and setuptools 84.2.1",
      "verified": "2026-11-12",
      "claims": ["python -m pip install -e path installs without copying files; the development directory is added to the import path", "Reinstall only when the project metadata changes", "Some backends (e.g. setuptools) leave build artifacts in the project directory"]
    },
    {
      "title": "install_requires vs requirements files",
      "url": "https://packaging.python.org/en/latest/discussions/install-requires-vs-requirements/",
      "version": "PyPA discussion, latest (fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["A project's declared requirements state what it minimally needs; pinning exact versions there is not best practice", "Requirements files often pin an exhaustive list for repeatable installs of a whole environment"]
    },
    {
      "title": "setuptools: Dependencies management",
      "url": "https://setuptools.pypa.io/en/latest/userguide/dependency_management.html",
      "version": "setuptools docs, latest (fetched 2026-11-12); local builds used setuptools 84.2.1",
      "verified": "2026-11-12",
      "claims": ["The same required-dependency declaration is shown as `dependencies` in pyproject.toml and `install_requires` in setup.py/setup.cfg", "Optional dependencies (extras) are declared in [project.optional-dependencies]"]
    },
    {
      "title": "Go Modules Reference",
      "url": "https://go.dev/ref/mod",
      "version": "Go modules reference (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["The module directive defines the main module's path", "The go directive sets the minimum Go version", "A require directive declares a minimum required version of a dependency"]
    }
  ]
}
---
## 1. One file that describes the project

In PY.M01.L02 you froze a venv into `requirements.txt`. That file records **what is installed** in one environment. It says nothing about the project itself: its name, which Python it needs, which commands it provides, which of those packages it actually needs and which are just tools.

`pyproject.toml` is that description. If you know Go, you already know its job:

| Go | Python |
|---|---|
| `go.mod`: `module example.com/shop` | `[project]` `name = "shopkit"` |
| `go 1.22` (minimum Go version) | `requires-python = ">=3.12"` |
| `require` (minimum versions) | `dependencies = ["httpx>=0.27"]` |
| exact versions recorded for a build | a pinned `requirements.txt` from `pip freeze` |
| `go install ./cmd/shop` | `[project.scripts]` plus `pip install` |
| `go build` | a **build backend** (setuptools, hatchling, …) |

A minimal, working file:

```toml
[build-system]
requires = ["setuptools >= 77.0.3"]
build-backend = "setuptools.build_meta"

[project]
name = "shopkit"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
shopkit = "shopkit.cli:main"
```

- `[build-system]`: pip doesn't build packages itself. It installs the `requires` list into a temporary environment and asks the `build-backend` to build. The packaging guide says this table should always be present.
- `[project]`: `name` is required. So is `version`, unless the backend computes it (`dynamic = ["version"]`).
- `[project.scripts]`: after installation, a `shopkit` command exists in the venv's `bin/`. It runs `main()` from the module `shopkit.cli`. The value is an **import path**, `module:function`, not a file path.

## 2. TOML: a key belongs to the last header above it

TOML looks like INI, with one rule to remember. `[a.b]` starts a table, and **every key below it belongs to that table until the next header**. Indentation and blank lines don't matter.

```quiz
{ "id": "q1", "type": "output", "label": "Debugging",
  "prompt": "What does this print? (tomllib is the standard library's TOML reader.)",
  "code": "import tomllib\ndoc = tomllib.loads(\"\"\"\n[project]\nname = \"notes\"\n\n[project.urls]\nHomepage = \"https://example.com\"\nrequires-python = \">=3.12\"\n\"\"\")\nprint(sorted(doc[\"project\"]))\nprint(doc[\"project\"][\"urls\"])",
  "answer": "['name', 'urls']\n{'Homepage': 'https://example.com', 'requires-python': '>=3.12'}",
  "explanation": "requires-python sits below the [project.urls] header, so TOML stores it as a URL named 'requires-python'. The project itself has no Python requirement. Keep all plain [project] keys above the first [project.something] header." }
```

You can check any pyproject.toml the same way: `python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb')))"`.

## 3. Layout: src or flat

Two common layouts:

```text
flat layout                 src layout
shopkit-repo/               shopkit-repo/
├── pyproject.toml          ├── pyproject.toml
├── shopkit/                ├── src/
│   ├── __init__.py         │   └── shopkit/
│   └── cli.py              │       ├── __init__.py
└── tests/                  │       └── cli.py
                            └── tests/
```

Recall L01: the current directory goes first on `sys.path`. In the flat layout, running Python from the repo root imports `shopkit/` **from the folder**, whether or not it's installed. So your tests might pass against files the installed package doesn't even include.

The src layout prevents that. From the root, `shopkit` isn't importable at all until you install the project:

```console
$ ls src
shopkit
$ python3 -c "import shopkit"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'shopkit'
```

This academy uses the src layout for installable projects. `src` is only a folder: you never write `import src.shopkit`. Import paths start **inside** `src/`.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "What does the src layout protect you from?",
  "options": [
    "Tests importing your package straight from the working folder instead of the installed version",
    "Circular imports between modules",
    "Having to write a pyproject.toml",
    "Name clashes between two installed distributions"
  ], "answer": 0,
  "explanation": "With the package under src/, the current directory on sys.path can't provide it. You have to install it (usually editable), so you always test what an install really contains." }
```

## 4. Editable installs: `pip install -e .`

During development you want the venv to use **your working files**, so an edit is live straight away with no reinstall after each change. That's an editable install:

```console
$ python3 -m venv .venv
$ .venv/bin/python -m pip install -e .
Obtaining file:///.../shopkit
  Installing build dependencies: started
  ...
Successfully built shopkit
Installing collected packages: shopkit
Successfully installed shopkit-0.1.0
$ .venv/bin/shopkit
shopkit v1
```

(Behind "Installing build dependencies", pip downloaded setuptools 84.2.1 into a temporary build environment, because of `requires`.)

Now change `print("shopkit v1")` to `v2` in `src/shopkit/cli.py` and run it again, **without reinstalling**:

```console
$ .venv/bin/shopkit
shopkit v2
$ cd /tmp && /path/to/.venv/bin/python -c "import shopkit; print(shopkit.__file__)"
/path/to/shopkit/src/shopkit/__init__.py
```

The import resolves to your source folder from any directory. What does need a reinstall is a **metadata** change: name, dependencies, or a new `[project.scripts]` entry. We added `shopkit-admin = "shopkit.cli:main"`, and the command didn't exist in `.venv/bin` until we ran `pip install -e .` again.

setuptools also writes a `src/shopkit.egg-info/` folder. That's a build artifact: add `*.egg-info/` to `.gitignore`.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "After `pip install -e .`, you must reinstall every time you edit a .py file in src/ before the change takes effect.", "answer": false,
  "explanation": "Editable means the venv points at your source folder, so code edits are live on the next run. Reinstall when metadata changes: dependencies, scripts, name." }
```

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "You added `report = \"shopkit.report:main\"` under [project.scripts] in an editably installed project. The shell says `report: command not found`. What do you do?",
  "options": [
    "Run `python -m pip install -e .` again",
    "Add src/ to PYTHONPATH",
    "Add an __init__.py to src/",
    "Rename report.py to __main__.py"
  ], "answer": 0,
  "explanation": "Commands are created at install time from the metadata. A new script entry is a metadata change, so reinstall. Code edits never need this." }
```

## 5. Dependencies: ranges in pyproject, pins in requirements

`[project] dependencies` answers "what does this project **need** to run?" Use minimum versions, sometimes with an upper bound (`"httpx>=0.27"`, `"pydantic>=2,<3"`). The PyPA advice: a project's declared requirements should be minimal, and pinning exact versions there isn't best practice. Exact pins in a library make it impossible to install alongside anything that pins differently.

A **requirements file** answers "what exactly is installed in *this* deployment?" `pip freeze` gives the full pinned list for repeatable installs (PY.M01.L02). Applications typically have both: pyproject for intent, a pinned file (or lock file) for the exact build.

Tools you need only while developing (pytest, Ruff) go in an **extra**:

```toml
[project.optional-dependencies]
dev = ["pytest>=8"]
```

```console
$ .venv/bin/python -m pip install -e ".[dev]"
...
Successfully installed iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.2.0 shopkit-0.1.0
```

Users who run `pip install shopkit` don't get pytest. You do, with `.[dev]`. The quotes stop your shell from treating the brackets as a pattern.

**Distribution name ≠ import name.** `name` is what pip installs and lists. What you `import` is the package folder. With `name = "shop-kit"` and the folder `src/shopkit/`:

```console
$ .venv/bin/python -m pip list | grep -i shop
shop-kit 0.1.0   /.../dist
$ .venv/bin/python -c "import shopkit; print('import shopkit OK')"
import shopkit OK
$ .venv/bin/python -c "import shop_kit"
ModuleNotFoundError: No module named 'shop_kit'
```

```quiz
{ "id": "q5", "type": "choice", "label": "Application",
  "prompt": "Your FastAPI service needs fastapi at runtime and pytest for tests. You also want CI to install exactly what passed yesterday. Which setup fits?",
  "options": [
    "dependencies = [\"fastapi>=0.115\"]; pytest in a dev extra; a pinned requirements file generated for CI",
    "dependencies = [\"fastapi==0.115.0\", \"pytest==9.2.0\"] and nothing else",
    "Everything only in requirements.txt and no pyproject.toml",
    "dependencies = [\"fastapi\", \"pytest\"] and run pip freeze in production"
  ], "answer": 0,
  "explanation": "Intent (minimum versions, runtime only) goes in pyproject. Dev tools go in an extra. Exact reproducibility comes from a separate pinned file. Pinning in dependencies, or making pytest a runtime dependency, mixes the two jobs." }
```

## 6. `[tool.*]`: one home for tool settings

Tools read their configuration from `[tool.<name>]` tables in the same file, e.g. `[tool.pytest.ini_options]` or `[tool.ruff]` (next lesson). Each tool documents its own keys. The `[project]` table is the standard part. Everything under `[tool]` belongs to the tool that reads it.

**Common mistakes**

- A plain `[project]` key placed under a sub-table header (section 2).
- `src.mypkg.cli:main` in `[project.scripts]`. It must be `mypkg.cli:main`.
- Exact pins (`==`) in `dependencies`, and dev tools listed as runtime dependencies.
- Forgetting to reinstall after changing dependencies or scripts.
- Committing `*.egg-info/` or `build/`.

## 7. Practice

The exercise gives you a src-layout project whose pyproject.toml has four mistakes, each from a section above. setuptools refuses to build it. The tests read the file with `tomllib`, so you need no network.

```exercise
PY.M06.L02.E1
```
