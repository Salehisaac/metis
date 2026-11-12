---
{
  "id": "OPS.M03.L01",
  "title": "Ruff: lint and format checks for CI",
  "difficulty": "intermediate",
  "minutes": 65,
  "prerequisites": ["OPS.M02"],
  "objectives": [
    "Run ruff check and ruff format --check and read their output and exit codes",
    "Configure Ruff in pyproject.toml with an explicit rule selection, and explain why explicit beats the version-dependent default",
    "Separate safe automatic fixes from findings that need judgment (B006, E722, S105)",
    "Explain why turning a rule off or adding noqa to make CI pass is usually the wrong fix"
  ],
  "why": "A CI pipeline is only as useful as the checks it runs. Ruff is fast enough to run on every push, and several of its rules catch real bugs you've already met in this academy: shared mutable defaults, bare excepts that hide errors, and hardcoded secrets. Before writing the pipeline, you need to know exactly what the commands do and when they fail.",
  "applications": [
    "A lint and format gate that fails a merge request before review",
    "Catching a hardcoded token (S105) before it is pushed, not after",
    "Consistent formatting without style debates in code review"
  ],
  "exercises": ["OPS.M03.L01.E1"],
  "sources": [
    {
      "title": "The Ruff Linter",
      "url": "https://docs.astral.sh/ruff/linter/",
      "version": "Ruff docs (current); installed ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": ["ruff check lints the given files or directories", "--fix applies only safe fixes by default; unsafe fixes need --unsafe-fixes", "Exit codes: 0 no violations (or all fixed), 1 violations found, 2 abnormal termination; --exit-zero", "noqa comments: # noqa: {code} per line, # ruff: noqa per file"]
    },
    {
      "title": "The Ruff Formatter",
      "url": "https://docs.astral.sh/ruff/formatter/",
      "version": "Ruff docs (current); installed ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": ["ruff format formats files in place", "ruff format --check writes nothing and exits 1 if files would be reformatted", "The formatter does not sort imports; use ruff check --select I --fix", "Designed as a drop-in replacement for Black"]
    },
    {
      "title": "Configuring Ruff",
      "url": "https://docs.astral.sh/ruff/configuration/",
      "version": "Ruff docs (current); installed ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": ["Settings live in pyproject.toml ([tool.ruff]), ruff.toml or .ruff.toml; the closest config file applies", "A pyproject.toml without a [tool.ruff] section is ignored", "Default line-length 88; default excludes include .git and .venv"]
    },
    {
      "title": "Ruff tutorial",
      "url": "https://docs.astral.sh/ruff/tutorial/",
      "version": "Ruff docs (current); installed ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": ["By default Ruff enables rules from F, E, B, UP and RUF and many more, omitting stylistic rules that overlap with the formatter"]
    },
    {
      "title": "Ruff rules index",
      "url": "https://docs.astral.sh/ruff/rules/",
      "version": "Ruff docs (current); installed ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": ["Prefixes: Pyflakes (F), pycodestyle (E, W), flake8-bugbear (B), flake8-bandit (S), flake8-logging-format (G), isort (I), pyupgrade (UP)"]
    },
    {
      "title": "Ruff rule B006: mutable-argument-default",
      "url": "https://docs.astral.sh/ruff/rules/mutable-argument-default/",
      "version": "Ruff docs (current); installed ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": ["Defaults are evaluated once at definition and the same mutable object is shared across calls", "The fix is unsafe: it replaces the default with None, which may not be what was intended"]
    },
    {
      "title": "Ruff rule S105: hardcoded-password-string",
      "url": "https://docs.astral.sh/ruff/rules/hardcoded-password-string/",
      "version": "Ruff docs (current); installed ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": ["Hardcoded passwords in source are a security risk; read them from the environment (os.environ) instead"]
    }
  ]
}
---
## 1. Two commands, two exit codes

Ruff is a linter and a formatter in one tool, and it's installed in the academy's venv (ruff 0.17.3). In CI you run two commands:

| Command | Does | Exit code |
|---|---|---|
| `ruff check` | reports rule violations (bugs, unused code, import order...) | 0 clean, 1 violations, 2 Ruff itself failed |
| `ruff format --check` | reports files the formatter *would* change, writes nothing | 0 formatted, 1 would reformat, 2 error |

**CI only reads the exit code.** Non-zero means the step fails, which fails the pipeline. That's the whole contract, and it's why `--exit-zero` (always 0) has no place in a CI gate.

On your machine you run the fixing versions: `ruff check --fix` and `ruff format` (formats in place).

Here is a small module from a reporting service. It has a few problems on purpose:

```python
import logging
import os
import json

log = logging.getLogger(__name__)
API_TOKEN = "tok_live_9f8e7d"

def load_report(path, cache={}):
    if path in cache: return cache[path]
    try:
        with open(path) as f:
            data = json.load(f)
    except:
        data = None
    if data == None:
        log.warning(f"empty report {path}")
    cache[path] = data
    return data
```

Selecting only the `E` and `F` rule families from the command line:

```console
$ ruff check --isolated --select E,F --output-format concise report.py
report.py:2:8: F401 [*] `os` imported but unused
report.py:9:21: E701 Multiple statements on one line (colon)
report.py:13:5: E722 Do not use bare `except`
report.py:15:16: E711 Comparison to `None` should be `cond is None`
Found 4 errors.
[*] 1 fixable with `--fix` (1 unsafe fix available with `--fix --unsafe-fixes`).
$ echo $?
1
```

Each line is `file:line:col: CODE message`. `[*]` marks an automatic fix. The default output format (`full`) shows code snippets too; `concise` is easier to read in CI logs. `--isolated` ignores config files, which is only useful for demos like this one.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A CI step runs `ruff check .` and Ruff prints `Found 3 errors.` What does the pipeline see?",
  "options": ["Exit code 1, so the step fails", "Exit code 3", "Exit code 0, because Ruff printed a summary", "Exit code 2"], "answer": 0,
  "explanation": "1 means violations were found, however many. 2 is reserved for Ruff itself failing: a bad config, a bad option or an internal error." }
```

## 2. Configure the rules explicitly

Ruff reads settings from the closest `pyproject.toml` that has a `[tool.ruff]` section (or `ruff.toml`). A typical team setup:

```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "B", "S", "G", "I"]
```

`E`/`F` are pycodestyle/pyflakes basics, `B` is bugbear (likely bugs), `S` is bandit (security), `G` is logging format and `I` is import sorting. With that file next to `report.py`:

```console
$ ruff check --output-format concise report.py
report.py:1:1: I001 [*] Import block is un-sorted or un-formatted
report.py:2:8: F401 [*] `os` imported but unused
report.py:6:13: S105 Possible hardcoded password assigned to: "API_TOKEN"
report.py:8:29: B006 Do not use mutable data structures for argument defaults
report.py:9:21: E701 Multiple statements on one line (colon)
report.py:13:5: E722 Do not use bare `except`
report.py:15:16: E711 Comparison to `None` should be `cond is None`
report.py:16:21: G004 Logging statement uses f-string
Found 8 errors.
[*] 2 fixable with `--fix` (2 unsafe fixes available with `--fix --unsafe-fixes`).
```

**Why `select` explicitly?** Without it, Ruff uses its built-in default set, which changes between Ruff versions. The tutorial now describes it as rules from F, E, B, UP, RUF "and many more", and the installed 0.17.3 enables 407 rules when no config is given (`ruff check --isolated --show-settings` lists them). If CI installs a newer Ruff than your laptop, the default set can differ. An explicit `select` plus a pinned Ruff version in `requirements.txt` means the same code gets the same verdict everywhere.

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "Without a `select` setting, every Ruff version checks exactly the same rules.", "answer": false,
  "explanation": "The default rule set is part of Ruff and has changed across versions. Pin the Ruff version and select rules explicitly so CI and laptops agree." }
```

## 3. Fixes: mechanical vs. judgment

`ruff check --fix` applies only **safe** fixes, ones meant to keep behaviour identical: removing an unused import, sorting imports, modernising annotations. **Unsafe** fixes need `--unsafe-fixes`, because they can change behaviour. Most rules worth having have no fix at all, because the right change depends on what you meant:

- **B006, mutable default** (`cache={}`): the default is evaluated *once*, when `def` runs, and the same dict is shared by every call. You met this in PY.M02 as aliasing. Here it's arguably intended as a cache, which is exactly why the fix is unsafe. Ruff can't know.
- **E722, bare `except:`** catches *everything*, including a `KeyboardInterrupt` or a typo's `NameError`, and turns it into `data = None`. Catch what you mean: `except (OSError, json.JSONDecodeError):`.
- **S105, hardcoded password**: the OPS.M02 lesson as a lint rule. The fix isn't a code edit, it's moving the value to the environment (`os.environ["API_TOKEN"]`) *and rotating it*, since it's already in Git history.
- **G004**: use `log.warning("empty report %s", path)` (OPS.M02.L02).

```quiz
{ "id": "q3", "type": "choice", "label": "Debugging",
  "prompt": "CI fails on `E722 Do not use bare except` in code that parses uploaded files. What's the right change?",
  "options": ["Catch the specific exceptions the parser raises, e.g. except (ValueError, OSError):", "Add # noqa: E722 to the line", "Change it to except Exception: pass", "Remove E from select"], "answer": 0,
  "explanation": "The rule exists because a bare except hides unrelated bugs. noqa or disabling E hides the finding; except Exception: pass still swallows bugs. Name the failures you actually expect." }
```

**`noqa` and `ignore` exist** (`# noqa: E722` on a line, `ignore = [...]` in config), and occasionally they're right, e.g. for a test that deliberately uses a pattern. But adding them to get a green pipeline converts a finding into a hidden one. In review, every `noqa` should have a reason next to it.

## 4. Formatting: no debates, one command

The formatter is designed as a drop-in replacement for Black: it decides line breaks, spacing and quotes, so code review doesn't have to. In CI it runs in check mode:

```console
$ ruff format --check report.py
unformatted: File would be reformatted
  --> report.py:8:1
   |
7  |
8  +
9  | def load_report(path, cache={}):
   -     if path in cache: return cache[path]
10 +     if path in cache:
11 +         return cache[path]
12 |     try:
   |

1 file would be reformatted
$ echo $?
1
```

Locally, `ruff format report.py` rewrites the file and the check passes. Two details:

- The formatter **doesn't sort imports**. That's lint rule `I001`, fixed by `ruff check --select I --fix` (or by `--fix` when `I` is selected).
- Run `ruff check --fix` *before* `ruff format`. Fixes can leave code the formatter would change; the other way round is rarely a problem.

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "`ruff format --check` fixes the formatting and then exits 0.", "answer": false,
  "explanation": "--check never writes files. It exits 1 if anything would be reformatted, which is what CI needs. Plain `ruff format` is the command that rewrites files." }
```

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "Imports are in the wrong order, `ruff format` has been run, and CI still fails. Which check is failing?",
  "options": ["ruff check with rule I001, because the formatter doesn't sort imports", "ruff format --check", "pytest", "None; the formatter sorted them"], "answer": 0,
  "explanation": "Import sorting belongs to the linter's I rules. Run ruff check --fix (with I selected) and then ruff format." }
```

## 5. Your turn

The exercise is code that fails the team's Ruff gate. The tests run the real `ruff check` and `ruff format --check` from the venv against the folder's `pyproject.toml`, plus behaviour tests. Some findings are cosmetic, and two are bugs. Use the tools for the mechanical part (`../../.venv/bin/ruff check --fix pricing.py`, `../../.venv/bin/ruff format pricing.py`) and your judgment for the rest.

```exercise
OPS.M03.L01.E1
```
