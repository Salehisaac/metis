```toml
[build-system]
requires = ["setuptools >= 77.0.3"]
build-backend = "setuptools.build_meta"

[project]
name = "pingwatch"
version = "0.1.0"
description = "Print the HTTP status of each URL"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27"]

[project.optional-dependencies]
dev = ["ruff>=0.17", "pytest>=8"]

[project.scripts]
pingwatch = "pingwatch.cli:main"
```

**The four mistakes**

1. **`dependencies` was in the wrong table.** In TOML a key belongs to the last `[header]` above it. Under `[project.scripts]` the line declared a *command* named `dependencies`, and setuptools rejected it: `configuration error: project.scripts.dependencies must be string`. Blank lines and distance don't matter, only the most recent header.
2. **`httpx==0.28.1` was an exact pin.** `[project] dependencies` says what the project *needs to run*. Pinning it exactly forces that one version onto every environment that installs pingwatch, and two packages with different pins can't be installed together. Use a minimum (`>=0.27`), and keep exact pins in a requirements file (`pip freeze`) for a reproducible deployment.
3. **pytest was a runtime dependency.** Everyone who installs pingwatch would get pytest. Development tools go in an extra (`[project.optional-dependencies] dev`), which you install with `python -m pip install -e ".[dev]"`.
4. **`src.pingwatch.cli:main` used a file path, not an import path.** With the src layout, the build backend installs the package `pingwatch` from `src/pingwatch/`, so the import name is `pingwatch.cli`. `src` is just a folder, not a package.

Verified in a throwaway venv: the starter fails at "Getting requirements to build editable" with error 1. This file installs (setuptools 84.2.1 pulled in by build isolation), and `pingwatch https://pypi.org/simple/` prints `200 https://pypi.org/simple/`.

**Alternatives:** `httpx>=0.27,<1` adds an upper bound, which is reasonable for a 0.x library whose minor releases may break things. Newer tooling also supports a `[dependency-groups]` table for development-only dependencies. The pip in this academy's venv (24.0) has no option to install them, so use an extra here.
