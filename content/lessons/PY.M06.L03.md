---
{
  "id": "PY.M06.L03",
  "title": "Ruff",
  "difficulty": "beginner",
  "minutes": 35,
  "prerequisites": ["PY.M06.L02"],
  "objectives": [
    "Run `ruff check` and read a diagnostic: location, rule code, fixable marker, exit status",
    "Apply safe fixes with --fix, and review unsafe fixes with --diff before accepting them",
    "Configure Ruff in [tool.ruff] / [tool.ruff.lint]: line-length, select vs extend-select, ignore, and target-version from requires-python",
    "Format code with `ruff format` and check formatting in CI with --check"
  ],
  "why": "Teams run a linter and a formatter on every commit and in CI, as Go teams run gofmt and go vet. Ruff does both for Python, and its rules catch real bugs, such as the mutable-default trap from PY.M02 or a bare except that swallows everything, before a reviewer has to.",
  "applications": [
    "A pre-commit or CI step: `ruff check .` and `ruff format --check .`",
    "Project-wide style settings in pyproject.toml so every contributor gets the same result",
    "Finding unused imports and variables left behind after a refactor"
  ],
  "exercises": ["PY.M06.L03.E1"],
  "sources": [
    {
      "title": "Ruff: The Ruff Linter",
      "url": "https://docs.astral.sh/ruff/linter/",
      "version": "Ruff docs, latest (~0.17.4); behaviour verified locally with ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": [
        "`ruff check` is the linter entry point and lints the current directory when given no path",
        "select sets the rule set; extend-select adds; ignore removes",
        "Only safe fixes are applied by default; --unsafe-fixes with --fix includes unsafe ones",
        "`# noqa: CODE` suppresses one violation on a line",
        "Exit codes: 0 no violations (or all fixed), 1 violations found, 2 abnormal termination"
      ]
    },
    {
      "title": "Ruff: The Ruff Formatter",
      "url": "https://docs.astral.sh/ruff/formatter/",
      "version": "Ruff docs, latest (~0.17.4); behaviour verified locally with ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": ["Drop-in replacement for Black; formats files in place", "`ruff format --check` exits 1 if any file would be reformatted", "The formatter doesn't sort imports; use the linter's I rules with --fix", "quote-style is configurable under [tool.ruff.format]"]
    },
    {
      "title": "Ruff: Configuring Ruff",
      "url": "https://docs.astral.sh/ruff/configuration/",
      "version": "Ruff docs, latest (~0.17.4); behaviour verified locally with ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": ["Configured in pyproject.toml ([tool.ruff]), ruff.toml or .ruff.toml", "Ruff uses the closest config file in the directory hierarchy", "Without target-version, Ruff falls back to the minimum version allowed by requires-python"]
    },
    {
      "title": "Ruff: Settings",
      "url": "https://docs.astral.sh/ruff/settings/",
      "version": "Ruff docs, latest (~0.17.4)",
      "verified": "2026-11-12",
      "claims": ["line-length default 88", "lint.extend-select adds rules to select", "format.quote-style default \"double\"", "lint.per-file-ignores maps file patterns to ignored codes"]
    },
    {
      "title": "Ruff 0.16.0 release notes",
      "url": "https://github.com/astral-sh/ruff/releases/tag/0.16.0",
      "version": "ruff 0.16.0 (released 2026-07-23)",
      "verified": "2026-11-12",
      "claims": ["Ruff 0.16 enables a much larger default rule set: 413 rules, up from 59", "Some opinionated E and F rules (e.g. E711, E712, E402) were removed from the defaults"]
    },
    {
      "title": "go command documentation (go vet, go fmt)",
      "url": "https://pkg.go.dev/cmd/go",
      "version": "cmd/go docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["go vet runs the vet tool and reports diagnostics", "go fmt runs gofmt -l -w on the named packages"]
    }
  ]
}
---
## 1. Two jobs, one tool

Go ships two tools you already use: `gofmt` rewrites code into the one standard layout, and `go vet` reports suspicious code. Ruff does both jobs for Python:

| Go | Ruff | Changes files? |
|---|---|---|
| `go vet ./...` | `ruff check .` | no (only with `--fix`) |
| `gofmt -l -w .` / `go fmt` | `ruff format .` | yes |
| `gofmt -l .` in CI | `ruff format --check .` | no |

Install it into the project's venv and run it with the venv's interpreter. A project lists it as a minimum in its `dev` extra (`ruff>=0.17`, as in L02). This academy pins the exact version in its venv, **ruff 0.17.3**, so your output matches the lesson's:

```console
$ .venv/bin/python -m pip install ruff==0.17.3
$ .venv/bin/python -m ruff --version
ruff 0.17.3
```

Below, `ruff` is short for `.venv/bin/python -m ruff` (or plain `ruff` with the venv activated).

## 2. `ruff check`: reading a diagnostic

```python
# weather.py
import json
import sys


def summary(readings):
    total = 0
    for i, value in enumerate(readings):
        total += value
    label = f"average"
    return label, total / len(readings)


def load_city(raw):
    try:
        return json.loads(raw)["city"]
    except KeyError:
        raise ValueError("no city in payload")
```

```console
$ ruff check --output-format concise weather.py
weather.py:2:8: F401 [*] `sys` imported but unused
weather.py:9:13: F541 [*] f-string without any placeholders
Found 2 errors.
[*] 2 fixable with `--fix`.
$ echo $?
1
```

Each line reads `file:line:column: CODE message`:

- The **code** names the rule. The letters say which family it comes from: `F` Pyflakes, `E`/`W` pycodestyle, `B` flake8-bugbear, `UP` pyupgrade, `I` isort, `SIM` simplify. `ruff rule F401` prints the rule's explanation and examples in the terminal.
- **`[*]`** means Ruff can fix it automatically.
- **Exit status** 1 means violations were found. 0 means clean, and 2 means Ruff itself failed (bad config, bad option). That's what CI looks at.

Without `--output-format concise` (the default "full" format), each diagnostic also shows the code snippet and the proposed fix.

**Which rules run?** Ruff 0.16 (July 2026) switched on a much larger default set: 413 rules, up from 59. Older tutorials and blog posts say the defaults are `E4, E7, E9, F`. That's no longer true. The defaults include some flake8-bugbear (`B`) rules, such as B006 for the mutable-default trap, but not all of them. The unused loop variable `i` (B007) and the `raise` inside `except` (B904) aren't in the default set, so they aren't flagged yet. Sections 3 and 4 add the whole `B` family.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "CI prints the line app/users.py:14:5: F841 Local variable `token` is assigned to but never used, and the job fails. What do you know?",
  "options": [
    "Line 14, column 5 of app/users.py breaks rule F841. There's no [*], so Ruff has no safe automatic fix, and Ruff exited with status 1",
    "The file failed to parse, so Ruff exited with 2",
    "Ruff already removed the variable, and the job fails only to tell you",
    "F841 is a formatting problem that `ruff format` will fix"
  ], "answer": 0,
  "explanation": "file:line:col, then the code. A missing [*] means no safe fix is offered. Violations make `ruff check` exit 1, which fails the CI step. The formatter never removes code." }
```

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "With ruff 0.17, if you don't configure any rules, `ruff check` runs only the E4, E7, E9 and F rules.", "answer": false,
  "explanation": "That was the default before 0.16. Since 0.16 the default set is much larger (413 rules in 0.16). Check what you're running with `ruff check --show-settings FILE` rather than trusting an old tutorial." }
```

## 3. `--fix`: safe and unsafe fixes

```console
$ ruff check --fix weather.py
Found 2 errors (2 fixed, 0 remaining).
$ ruff check weather.py
All checks passed!
```

By default, `--fix` applies only **safe** fixes, the ones that can't change what the code does: removing an unused import, dropping a useless `f`. Some rules have **unsafe** fixes that *might* change meaning. Ruff only lists them. To see one, go back to the original weather.py (before `--fix`) and add the `B` family for one run:

```console
$ ruff check --extend-select B --output-format concise weather.py
weather.py:2:8: F401 [*] `sys` imported but unused
weather.py:7:9: B007 Loop control variable `i` not used within loop body
weather.py:9:13: F541 [*] f-string without any placeholders
weather.py:17:9: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
Found 4 errors.
[*] 2 fixable with `--fix` (1 unsafe fix available with `--fix --unsafe-fixes`).
```

Never accept unsafe fixes blind. Preview them first with `--diff`, which doesn't touch the file:

```console
$ ruff check --extend-select B --unsafe-fixes --diff weather.py
--- weather.py
+++ weather.py
@@ -1,12 +1,11 @@
 import json
-import sys
 
 
 def summary(readings):
     total = 0
-    for i, value in enumerate(readings):
+    for _i, value in enumerate(readings):
         total += value
-    label = f"average"
+    label = "average"
     return label, total / len(readings)
 

Would fix 3 errors.
```

B904 has no automatic fix at all: you decide between `raise ... from err` and `raise ... from None`.

Renaming `i` to `_i` (B007, "loop variable not used") is harmless here. It would break code that reads `i` after the loop, which is why Ruff calls it unsafe. A leading underscore tells readers and Ruff that a name is **deliberately unused** (the same convention as L01).

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "Why doesn't plain `ruff check --fix` apply every fix Ruff knows about?",
  "options": [
    "Unsafe fixes may change behaviour, so they need --unsafe-fixes, and you should review them (e.g. with --diff)",
    "Fixes are only applied in files that are already formatted",
    "Each run fixes one rule, so you have to run it repeatedly",
    "Fixes require a [tool.ruff] table in pyproject.toml"
  ], "answer": 0,
  "explanation": "Safe fixes keep the meaning. Unsafe ones might not, so they're opt-in. Even then, the --diff preview is your code review." }
```

## 4. Configure it in pyproject.toml

Ruff reads `[tool.ruff]` from the **closest** pyproject.toml (or `ruff.toml`) above the file it checks. Here the weather project turns on bugbear and silences F541. The output below is for the original weather.py, before any fixes:

```toml
[project]
name = "weather"
version = "0.1.0"
requires-python = ">=3.12"

[tool.ruff]
line-length = 100

[tool.ruff.lint]
extend-select = ["B"]
ignore = ["F541"]
```

```console
$ ruff check --output-format concise
weather.py:2:8: F401 [*] `sys` imported but unused
weather.py:7:9: B007 Loop control variable `i` not used within loop body
weather.py:17:9: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
Found 3 errors.
[*] 1 fixable with `--fix` (1 unsafe fix available with `--fix --unsafe-fixes`).
```

- `line-length` is shared: the formatter wraps at it, and the E501 line-too-long rule (if selected) checks it. The default is 88.
- `extend-select` **adds** to the defaults. `select` **replaces** them: with `select = ["B"]` only B007 and B904 would be reported here, and F401 would disappear.
- `ignore` removes codes. `[tool.ruff.lint.per-file-ignores]` does it for matching files only, e.g. `"tests/*" = ["S101"]`.
- No `target-version`? Ruff uses `requires-python`. `ruff check --show-settings weather.py` shows `unresolved_target_version = 3.12`. So the `UP` rules suggest only syntax your minimum Python supports.

To silence **one** line on purpose, add `# noqa: CODE` to that line, always with the code. It's a last resort, for when the rule is wrong in this one spot. If you find yourself adding many, change the config instead.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "With the config above, you change `extend-select = [\"B\"]` to `select = [\"B\"]` and keep `ignore = [\"F541\"]`. Which codes does `ruff check` report for weather.py?",
  "options": ["B007 and B904 only", "F401, B007 and B904", "F401 and F541 only", "Nothing: ignore wins over select"], "answer": 0,
  "explanation": "select replaces the default set, so the F rules (including F401) no longer run. Only the B rules remain. We ran it: 2 errors, B007 and B904." }
```

## 5. `ruff format`

The formatter is Black-compatible and, like gofmt, mostly not up for debate. You run it, you don't argue with it:

```console
$ cat fmt.py
def area(w,h):
    return w*h
points = {'a':1, 'b' : 2}
$ ruff format --check fmt.py
...
1 file would be reformatted
$ echo $?
1
$ ruff format fmt.py
1 file reformatted
$ cat fmt.py
def area(w, h):
    return w * h


points = {"a": 1, "b": 2}
```

Spaces around operators, two blank lines between top-level definitions, double quotes (`quote-style` under `[tool.ruff.format]` can change that). `--check` changes nothing and exits 1 if any file *would* change, which is what CI runs. `--diff` shows the changes instead.

One thing the formatter does **not** do is sort imports. That's lint rule `I001`, which is on by default in 0.17, so `ruff check --fix` handles it:

```console
$ cat order.py
import sys
import json

print(json.dumps(sys.argv[1:]))
$ ruff format order.py
1 file left unchanged
$ ruff check --output-format concise order.py
order.py:1:1: I001 [*] Import block is un-sorted or un-formatted
```

The usual sequence, before every commit, is `ruff check --fix .` and then `ruff format .`.

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "`ruff format` also sorts your imports.", "answer": false,
  "explanation": "The formatter leaves import order alone. Import sorting is the linter's I001 rule: run `ruff check --fix` (I001 is on by default since 0.16; older setups add `--select I`)." }
```

```quiz
{ "id": "q6", "type": "choice", "label": "Application",
  "prompt": "You add two CI steps: `ruff check .` and `ruff format --check .`. A teammate's pull request fails only the second step. What should they do?",
  "options": [
    "Run `ruff format .` locally and commit the result",
    "Add `# noqa` to every reported file",
    "Remove the format step from CI",
    "Run `ruff check --unsafe-fixes --fix .`"
  ], "answer": 0,
  "explanation": "`format --check` failing means some file isn't in the standard layout. Formatting it locally and committing fixes the step. noqa is for lint rules, and lint already passed." }
```

## 6. Practice

The exercise uses a fixed rule set on the command line (`--isolated --select ...`), so no config file can change the result. Expect a mix: some fixes are automatic, some need you, and one rule points at a real bug that a test also catches.

```exercise
PY.M06.L03.E1
```
