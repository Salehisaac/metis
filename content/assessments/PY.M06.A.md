---
{ "id": "PY.M06.A", "module": "PY.M06", "title": "PY.M06 module assessment: modules, packages, pyproject, Ruff", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before PY.M07.

```quiz
{ "id": "a1", "type": "output",
  "prompt": "cfg.py contains only `items = []`. What does this print?",
  "code": "import sys, tempfile, pathlib\nd = tempfile.mkdtemp()\npathlib.Path(d, \"cfg.py\").write_text(\"items = []\\n\")\nsys.path.insert(0, d)\nimport cfg\nfrom cfg import items\nitems.append(\"x\")\nimport cfg as again\nprint(again.items, again is cfg)",
  "answer": "['x'] True",
  "explanation": "A module runs once and is cached in sys.modules, so every import returns the same module object. `from cfg import items` binds a second name to the same list, so appending through it is visible as cfg.items (aliasing, as in PY.M02)." }
```

```quiz
{ "id": "a2", "type": "choice", "label": "Debugging",
  "prompt": "From the project root, `python3 app/main.py` fails with `ImportError: attempted relative import with no known parent package` on the line `from .routes import router`. What's the right fix?",
  "options": [
    "Run it as a module from the root: `python3 -m app.main`",
    "Change the import to `import .routes`",
    "Delete app/__init__.py",
    "Add `sys.path.append('..')` at the top of main.py"
  ], "answer": 0,
  "explanation": "Run as a file, main.py is just __main__ with no package, so a relative import has nothing to be relative to. With -m app.main, Python imports the package app first. `import .x` is a SyntaxError, and editing sys.path hides the problem rather than fixing it." }
```

```quiz
{ "id": "a3", "type": "choice",
  "prompt": "`ImportError: cannot import name 'Order' from partially initialized module 'shop.models' (most likely due to a circular import)`. What does 'partially initialized' mean here?",
  "options": [
    "shop.models was already in sys.modules but hadn't finished running, so `Order` wasn't defined yet when another module asked for it",
    "shop.models has a syntax error after the line that defines Order",
    "shop/models.py is missing an __init__.py",
    "Order is defined twice in shop.models"
  ], "answer": 0,
  "explanation": "A module goes into sys.modules before its body runs. When the body imports a module that imports it back, the second import gets the half-run module. Fix it by moving the shared code into a module that imports neither." }
```

```quiz
{ "id": "a4", "type": "output", "label": "Debugging",
  "prompt": "What does this print?",
  "code": "import tomllib\ndoc = tomllib.loads(\"[project]\\nname = \\\"api\\\"\\n\\n[project.optional-dependencies]\\ndev = [\\\"pytest>=8\\\"]\\ndependencies = [\\\"fastapi>=0.115\\\"]\\n\")\nprint(doc[\"project\"].get(\"dependencies\"))\nprint(sorted(doc[\"project\"][\"optional-dependencies\"]))",
  "answer": "None\n['dependencies', 'dev']",
  "explanation": "The dependencies line comes after the [project.optional-dependencies] header, so it defines an extra called 'dependencies'. The project itself declares no runtime dependencies, and `pip install api` wouldn't install fastapi." }
```

```quiz
{ "id": "a5", "type": "truefalse",
  "prompt": "For reproducible installs, a project's `[project] dependencies` should pin exact versions, e.g. `\"fastapi==0.115.0\"`.", "answer": false,
  "explanation": "dependencies says what the project minimally needs, so use lower bounds (and upper bounds where known). Exact reproducibility belongs in a pinned requirements or lock file for one deployment." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "A teammate wants CI to (1) fail on lint problems and (2) fail on unformatted code, without CI changing any files. Which two Ruff commands go in CI? What do they run locally before pushing, and why shouldn't they just add `--unsafe-fixes` everywhere?",
  "model": "CI runs `ruff check .` (exit 1 on violations) and `ruff format --check .` (exit 1 if any file would be reformatted). Neither modifies files. Locally they run `ruff check --fix .` and then `ruff format .`. Unsafe fixes may change behaviour, so preview them with `--unsafe-fixes --diff` and apply them only after review.",
  "explanation": "check is the linter (like go vet), format is the formatter (like gofmt). --check turns the formatter into a CI gate. Safe fixes are automatic; unsafe ones need a human." }
```
