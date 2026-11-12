---
{
  "id": "PY.M06.L01",
  "title": "Imports, modules, packages, __main__",
  "difficulty": "intermediate",
  "minutes": 45,
  "prerequisites": ["PY.M01.L01"],
  "objectives": [
    "Explain what `import` does: search sys.path, run the module once, cache it in sys.modules",
    "Predict sys.path[0] for `python file.py`, `python -m pkg` and `python -c`, and diagnose ModuleNotFoundError and name shadowing",
    "Build a package with __init__.py, relative imports and a __main__.py that runs with `python -m pkg`",
    "Recognise a circular import from its error message and remove it by moving the shared code",
    "Use the leading-underscore convention, and explain how it differs from Go's exported names and internal/"
  ],
  "why": "Every FastAPI project is a package of many modules: routers, models, settings, services. Most 'it works on my machine' import errors (ModuleNotFoundError, relative imports with no known parent package, partially initialized module) come from not knowing where Python looks for modules and when module code runs.",
  "applications": [
    "Splitting an app into app/routers, app/models and app/settings without import errors",
    "Shipping a CLI that runs with `python -m yourtool`",
    "Diagnosing circular imports between models and services"
  ],
  "exercises": ["PY.M06.L01.E1"],
  "sources": [
    {
      "title": "Python Tutorial: Modules",
      "url": "https://docs.python.org/3.12/tutorial/modules.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "sys.path starts with the script's directory (or the current directory when no file is given), then PYTHONPATH, then site-packages",
        "A module's top-level statements run only the first time it is imported",
        "__init__.py makes a directory a regular package",
        "Relative imports use leading dots and only the `from ... import` form; the main module must use absolute imports",
        "`from module import *` imports all names except those beginning with an underscore"
      ]
    },
    {
      "title": "The import system",
      "url": "https://docs.python.org/3.12/reference/import.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "sys.modules is checked first and caches every imported module",
        "A module is added to sys.modules before its code runs, which prevents unbounded recursion on circular imports",
        "Importing parent.one implicitly executes parent/__init__.py first",
        "`import .x` is invalid; relative imports only use `from . import`"
      ]
    },
    {
      "title": "__main__: Top-level code environment",
      "url": "https://docs.python.org/3.12/library/__main__.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": [
        "`python -m pkg` runs pkg/__main__.py",
        "__main__.py is usually kept short, imports its functions from other modules, and isn't fenced with an if __name__ guard",
        "__main__.py may use relative imports such as `from .student import search_students`"
      ]
    },
    {
      "title": "The Go Programming Language Specification",
      "url": "https://go.dev/ref/spec",
      "version": "Go spec (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["It is illegal for a package to import itself, directly or indirectly", "An identifier is exported if its first character is an uppercase letter"]
    },
    {
      "title": "go command: Internal Directories",
      "url": "https://pkg.go.dev/cmd/go",
      "version": "cmd/go docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Code in or below a directory named internal is importable only by code that shares the import path above internal"]
    }
  ]
}
---
## 1. A module is a file, and importing it runs it

In Go, a **package** is a directory: every `.go` file in it shares one namespace, and you import the directory.
In Python the unit is smaller. A **module** is one `.py` file, and every module has its own namespace. A **package** is a directory of modules (section 3).

What `import greet` does, step by step:

1. Look in `sys.modules`, the cache of already-imported modules. If `greet` is there, reuse it and stop.
2. Otherwise, search the directories in `sys.path` for `greet.py`.
3. Create a module object, **put it into `sys.modules`**, then run the file top to bottom.
4. Bind the name `greet` in the importing module.

So a module's top-level code runs **once per process**, however many times it's imported:

```console
$ cat greet.py
print("loading greet")
NAME = "greet module"
$ cat main.py
import greet
import greet
import sys
print(greet.NAME)
print("greet" in sys.modules)
$ python3 main.py
loading greet
greet module
True
```

This is why a module-level `print`, database connection or config read happens exactly once, on first import, and not again. It's also why the REPL doesn't pick up your edits to a module until you restart it.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "This writes a tiny module into a temporary folder, puts the folder on sys.path, and imports the module twice. What does it print?",
  "code": "import sys, tempfile, pathlib\nd = tempfile.mkdtemp()\npathlib.Path(d, \"counter.py\").write_text(\"print(\\\"loading counter\\\")\\nhits = 0\\n\")\nsys.path.insert(0, d)\nimport counter\ncounter.hits += 1\nimport counter\nprint(counter.hits)",
  "answer": "loading counter\n1",
  "explanation": "The second import finds counter in sys.modules and returns the same module object. The file doesn't run again, so 'loading counter' prints once, and hits stays 1. It isn't reset to 0." }
```

## 2. Where Python looks: sys.path

`sys.path` is a plain list of directories, searched in order. It starts with:

1. **The directory of the script you ran** (`python3 tools/report.py` puts `tools/` first). With `-m` or `-c`, it's the **current directory** instead.
2. Directories in the `PYTHONPATH` environment variable, if set.
3. The interpreter's `site-packages`, where `pip install` puts things (in a venv, the venv's own `site-packages`).

```console
$ cd l01
$ python3 a/p.py          # p.py prints sys.path[0]
.../l01/a
$ python3 -m a.p
.../l01
```

**ModuleNotFoundError** means none of those directories contains the name. Check *which* directory comes first before you blame the package.

**Shadowing.** Because your script's directory comes first, a file of yours can hide a standard-library module. Here's a file called `random.py`:

```console
$ cat random.py
# my experiment with random numbers
import random

print(random.choice([1, 2, 3]))
$ python3 random.py
Traceback (most recent call last):
  File ".../shadow/random.py", line 2, in <module>
    import random
  File ".../shadow/random.py", line 4, in <module>
    print(random.choice([1, 2, 3]))
          ^^^^^^^^^^^^^
AttributeError: partially initialized module 'random' has no attribute 'choice' (most likely due to a circular import)
```

`import random` found **this file**, not the standard library's. The message blames a circular import, and technically that's true: the file imported itself. The real fix is to rename the file. Never name your modules `random.py`, `json.py`, `email.py`, `test.py` and so on.

```quiz
{ "id": "q2", "type": "choice",
  "prompt": "From the repository root you run `python3 scripts/seed.py`. seed.py contains `import app`, and the package app/ is at the repository root. What happens, and why?",
  "options": [
    "ModuleNotFoundError: sys.path[0] is scripts/, not the repository root",
    "It works, because the current directory is always on sys.path",
    "It works, because Python searches parent directories upward",
    "SyntaxError: imports must be relative inside scripts/"
  ], "answer": 0,
  "explanation": "Running a file puts that file's directory first (scripts/), not the directory you're standing in. Python never searches upward. Use `python3 -m scripts.seed` from the root (then sys.path[0] is the current directory), or install the project (L02)." }
```

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "A file named json.py contains `import json` and `print(json.dumps({}))`. Running it gives `AttributeError: partially initialized module 'json' has no attribute 'dumps' (most likely due to a circular import)`. What's the fix?",
  "options": [
    "Rename the file, e.g. to json_demo.py",
    "Move `import json` inside a function",
    "Reinstall Python, because the standard library json module is broken",
    "Write `from . import json`"
  ], "answer": 0,
  "explanation": "The script's directory is first on sys.path, so `import json` imported the file itself, half-run, instead of the standard library. Renaming removes the shadowing. (Delete any __pycache__ copy too.)" }
```

## 3. Packages, `__init__.py` and relative imports

A **regular package** is a directory with an `__init__.py` file. The file can be empty. Its presence says "this directory is an importable package":

```text
proj/
└── shop/
    ├── __init__.py      # print("running shop/__init__.py")
    ├── pricing.py       # VAT = 0.2; def with_vat(net) -> float
    ├── cli.py           # def main(): uses with_vat
    └── __main__.py      # section 4
```

`import shop.pricing` first runs `shop/__init__.py`, then `shop/pricing.py`. Use `__init__.py` for package-wide setup or re-exports, and keep it small, since it runs the first time anything in the package is imported (once per process, as in section 1).

(Python also has *namespace packages*, directories without `__init__.py`. They're for splitting one package across several folders, an advanced feature. Add the `__init__.py`.)

Inside the package, `cli.py` imports its sibling with a **relative import**:

```python
# shop/cli.py
import sys

from .pricing import with_vat


def main() -> int:
    net = float(sys.argv[1])
    print(f"{net} -> {with_vat(net)} incl. VAT")
    return 0
```

The dot means "my own package". `from .pricing import with_vat` keeps working if you rename `shop` or move it into a bigger project. Two dots (`from ..core import x`) mean the parent package. The absolute spelling, `from shop.pricing import with_vat`, also works but hard-codes the package name.

Relative imports only work in the `from ... import` form. `import .pricing` is a SyntaxError.

They also need Python to *know* the package, which it doesn't if you run the file directly:

```console
$ python3 shop/cli.py 10
Traceback (most recent call last):
  File ".../proj/shop/cli.py", line 3, in <module>
    from .pricing import with_vat
ImportError: attempted relative import with no known parent package
```

Run as a file, `cli.py` is just the top-level script `__main__`, with no parent package. Run modules inside a package with `-m` and the dotted name, from the directory that *contains* the package.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "Inside a package, `import .pricing` is a valid way to import the sibling module pricing.py.", "answer": false,
  "explanation": "Relative imports only exist in the from-form: `from . import pricing` or `from .pricing import with_vat`. `import .pricing` is a SyntaxError." }
```

## 4. `python -m pkg` and `__main__.py`

Go has `package main` with `func main()`. A Python package becomes runnable with a `__main__.py` file. `python -m shop` imports the package, then runs `shop/__main__.py` as `__main__`:

```python
# shop/__main__.py
import sys

from .cli import main

sys.exit(main())
```

```console
$ python3 -m shop 10
running shop/__init__.py
10.0 -> 12.0 incl. VAT
$ echo $?
0
```

The `__main__` docs recommend keeping this file short, with no `if __name__ == "__main__":` guard: real logic lives in other modules, where tests can import it. `sys.exit(main())` turns `main`'s return value into the process exit status, like `os.Exit(code)` in Go.

Two ways to get it wrong:

```console
$ python3 shop 10                  # a folder path, not a module name
...
ImportError: attempted relative import with no known parent package
$ cd shop && python3 -m shop 10    # standing inside the package
/usr/bin/python3: No module named shop
```

`-m` needs the **dotted module name**, and the **parent** of the package must be on `sys.path`, which is the current directory for `-m`.

```quiz
{ "id": "q4", "type": "output", "label": "Debugging",
  "prompt": "Same shop package as above (shop/cli.py defines main() but never calls it; __init__.py prints a line). From proj/ you run `python3 -m shop.cli 10`. What is printed?",
  "code": "# python3 -m shop.cli 10",
  "answer": "running shop/__init__.py",
  "explanation": "-m shop.cli imports the package (running __init__.py), then runs cli.py as __main__. cli.py only *defines* main() and has no code that calls it, so nothing else happens, and the exit status is 0. That's why the call lives in __main__.py: `python3 -m shop`." }
```

## 5. Circular imports

Go refuses to compile an import cycle. Python allows one, and it fails **at runtime**, depending on which module happens to be imported first. Here `posts` and `authors` (in package `blog`) import from each other:

```python
# blog/posts.py
from .authors import display_name

DEFAULT_AUTHOR = "anon"


def byline(author: str) -> str:
    return f"by {display_name(author)}"
```

```python
# blog/authors.py
from .posts import DEFAULT_AUTHOR


def display_name(author: str) -> str:
    return (author or DEFAULT_AUTHOR).title()
```

```console
$ python3 -c "from blog.posts import byline"
Traceback (most recent call last):
  File ".../blog/posts.py", line 1, in <module>
    from .authors import display_name
  File ".../blog/authors.py", line 1, in <module>
    from .posts import DEFAULT_AUTHOR
ImportError: cannot import name 'DEFAULT_AUTHOR' from partially initialized module 'blog.posts' (most likely due to a circular import)
```

Replay section 1's steps. `blog.posts` goes into `sys.modules` and starts running. Its **first line** imports `authors`, which asks `posts` for `DEFAULT_AUTHOR`. `posts` is in the cache, but only its first line has run, so the name doesn't exist yet: the module is **partially initialized**. Import `blog.authors` first instead, and the same cycle fails the other way round (`cannot import name 'display_name'`).

**Fix: move what both modules need into a third module** that imports neither:

```python
# blog/settings.py
DEFAULT_AUTHOR = "anon"
```

`authors` now imports `from .settings import DEFAULT_AUTHOR`, and `posts` drops the constant. The imports form a one-way chain, posts → authors → settings, and work in any order:

```console
$ python3 -c "from blog.posts import byline; print(byline('ada')); print(byline(''))"
by Ada
by Anon
```

Patching only one side, e.g. `from . import posts` plus `posts.DEFAULT_AUTHOR` inside the function, made `from blog.posts import byline` work in our test. `from blog.authors import display_name` still failed with the same error. Restructure; don't juggle import styles.

```quiz
{ "id": "q6", "type": "choice", "label": "Application",
  "prompt": "app/models.py imports `hash_password` from app/services.py, and services.py imports `User` from models.py at the top. Now the app fails with 'cannot import name ... from partially initialized module'. What's the most robust fix?",
  "options": [
    "Move hash_password (and anything else both need) into a new module, e.g. app/security.py, that imports neither",
    "Swap the order of the import lines in both files",
    "Wrap both imports in try/except ImportError",
    "Merge the two files into one 3,000-line module"
  ], "answer": 0,
  "explanation": "Removing the cycle makes the dependency graph one-way, like Go forces you to. Reordering only changes which entry point breaks. try/except leaves names undefined. Merging works but destroys the structure." }
```

## 6. Private by convention: the leading underscore

Go enforces visibility with the compiler. Lowercase identifiers aren't exported, and code under `internal/` is importable only from the tree above it. Python enforces neither. The convention is a **leading underscore**: `_clean()` or `_cache` means "internal, don't use it from outside". A package or module name can start with `_` too (`app/_db.py`).

The language honours it in one place: `from module import *` skips underscore names. A plain `import` or `from module import _name` still works. It's a signpost for humans and linters, not a lock.

```quiz
{ "id": "q7", "type": "output",
  "prompt": "tools.py defines slug() and _clean(). What does this print?",
  "code": "import sys, tempfile, pathlib\nd = tempfile.mkdtemp()\npathlib.Path(d, \"tools.py\").write_text(\"def slug(s):\\n    return s.lower()\\n\\n\\ndef _clean(s):\\n    return s.strip()\\n\")\nsys.path.insert(0, d)\nfrom tools import *\nprint(slug(\"Hi\"), \"_clean\" in globals())\nimport tools\nprint(tools._clean(\"  ok  \"))",
  "answer": "hi False\nok",
  "explanation": "`import *` brings in only names without a leading underscore, so _clean isn't defined in the importer. But nothing stops `tools._clean(...)`: the underscore is a convention, unlike Go's compiler-checked exported names." }
```

**Common mistakes, summarised**

- Running a package's module as a file (`python3 pkg/cli.py`). Use `python3 -m pkg.cli` from the package's parent.
- Naming a file after a standard-library module.
- Heavy work at import time (network calls, reading big files) in `__init__.py` or at module level. It runs on first import, including in every test run.
- Two modules that import each other. Move the shared part out.

## 7. Practice

Your exercise: three loose scripts must become a runnable package. Expect several different import errors on the way. Read each traceback against sections 2–5.

```exercise
PY.M06.L01.E1
```
