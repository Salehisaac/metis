---
{
  "id": "PY.M01.L02",
  "title": "venv and pip: why isolate dependencies",
  "difficulty": "beginner",
  "minutes": 30,
  "prerequisites": ["PY.M01.L01"],
  "objectives": [
    "Explain why each project gets its own virtual environment, compared with Go modules",
    "Create a venv and use it with or without activation",
    "Install packages with `python -m pip` into the right environment, and tell which interpreter is running",
    "Record dependencies in requirements.txt and recreate an environment from it"
  ],
  "why": "\"Works on my machine\" bugs usually come from the wrong interpreter or the wrong package versions. Every FastAPI project you build will have its own environment, and knowing which Python and pip you're running saves hours of confusion.",
  "applications": [
    "One isolated environment per service or exercise",
    "Reproducible installs in CI and Docker images from requirements.txt",
    "Diagnosing ModuleNotFoundError and 'it's installed but Python can't find it'"
  ],
  "exercises": [],
  "sources": [
    {
      "title": "venv: Creation of virtual environments",
      "url": "https://docs.python.org/3.12/library/venv.html",
      "version": "Python 3.12 (docs 3.12.16; installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Each venv has its own independent set of installed packages", "Created with python -m venv PATH", "Activation isn't required; you can use the venv interpreter's full path", "sys.prefix != sys.base_prefix inside a venv", "Venvs aren't committed or moved; recreate them instead"]
    },
    {
      "title": "pip User Guide",
      "url": "https://pip.pypa.io/en/stable/user_guide/",
      "version": "pip docs v26.3; behaviour also verified locally with pip 24.0",
      "verified": "2026-11-12",
      "claims": ["python -m pip runs pip with that specific interpreter", "pip install -r installs from a requirements file", "pip freeze outputs pinned versions in requirements format"]
    },
    {
      "title": "Externally Managed Environments (PyPA specification)",
      "url": "https://packaging.python.org/en/latest/specifications/externally-managed-environments/",
      "version": "PyPA specification (from PEP 668); Ubuntu's Python 3.12.3 ships the marker",
      "verified": "2026-11-12",
      "claims": ["With the EXTERNALLY-MANAGED marker, pip refuses to install outside a virtual environment", "The error message should point users to a virtual environment"]
    }
  ]
}
---
## 1. The problem: one Python, many projects

In Go, each module has its own `go.mod`, and the build uses exactly those versions. You never install a library "into Go".

Python's default is the opposite. Packages install into a `site-packages` folder belonging to **one interpreter**, shared by everything that uses that interpreter. If two projects need different versions of the same library, they fight.

A **virtual environment (venv)** fixes this. It's a folder containing its own `python` and its own `site-packages`. Each project gets one, so its packages don't leak into, or depend on, anything else.

Your system's Python protects itself, too. On this machine (Ubuntu), a system-wide install is refused:

```console
$ python3 -m pip install requests
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.

    If you wish to install a non-Debian-packaged Python package,
    create a virtual environment using python3 -m venv path/to/venv.
```

That's not a bug to work around with `--break-system-packages`. It's telling you to use a venv.

## 2. Create one and use it

```console
$ python3 -m venv .venv                  # creates the folder .venv/
$ .venv/bin/python -c "import sys; print(sys.prefix != sys.base_prefix)"
True
```

`sys.prefix` points at the environment that's running, and `sys.base_prefix` at the Python it was created from. They differ only inside a venv, which makes this the quickest "am I in the venv?" check. With the system `python3` the same line prints `False`.

**Activation is optional.** `source .venv/bin/activate` mainly puts `.venv/bin` first on your PATH (it also sets `VIRTUAL_ENV` and changes your prompt), so plain `python` and `pip` mean the venv's copies:

```console
$ source .venv/bin/activate
(.venv) $ which python
/your/project/.venv/bin/python
(.venv) $ deactivate
```

Calling `.venv/bin/python` directly works without activating. That's what scripts, CI and this academy's commands do, because it can't silently pick the wrong interpreter.

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "You must activate a virtual environment before you can use it.", "answer": false,
  "explanation": "Activation mainly changes PATH. `.venv/bin/python ...` uses the venv directly, and installed tools in .venv/bin work without activation too." }
```

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print, run from a project where .venv was created with python3 -m venv?",
  "code": "# .venv/bin/python -c \"import sys; print(sys.prefix != sys.base_prefix)\"",
  "answer": "True",
  "explanation": "Inside a venv, sys.prefix is the venv folder and sys.base_prefix is the original Python, so they differ." }
```

## 3. Install with `python -m pip`

```console
$ .venv/bin/python -m pip install requests
```

Why `-m pip` and not `pip`? As you saw in L01, `-m` runs the module **belonging to that exact interpreter**. A bare `pip` is whatever comes first on your PATH: maybe another venv, maybe the system's.

The classic bug: `pip install x` succeeds, then `python app.py` says `ModuleNotFoundError: No module named 'x'`. The package went into one environment and your code ran in another.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Which command is guaranteed to install requests into this project's .venv, whatever is activated?",
  "options": [".venv/bin/python -m pip install requests", "pip install requests", "sudo pip install requests", "python3 -m venv requests"], "answer": 0,
  "explanation": "Naming the venv's interpreter and using -m pip leaves no doubt. Bare pip depends on PATH. sudo pip tries to modify the system Python. venv creates environments; it doesn't install packages." }
```

## 4. Make it reproducible: requirements.txt

A venv is **disposable**. Don't commit it and don't copy it to another machine, because it contains absolute paths. Commit the list of what to install instead:

```console
$ .venv/bin/python -m pip install iniconfig==2.0.0
$ .venv/bin/python -m pip freeze > requirements.txt
$ cat requirements.txt
iniconfig==2.0.0
$ rm -rf .venv && python3 -m venv .venv
$ .venv/bin/python -m pip install -r requirements.txt   # same versions back
```

`pip freeze` lists exact pinned versions, so the file works like a simple lockfile: everyone gets the same versions (in Go, `go.mod` pins versions and `go.sum` adds checksums). Later you'll meet `pyproject.toml` (PY.M06), which declares what your project needs, while a frozen requirements file records what was installed.

**Common mistakes**

- Committing `.venv/`. It's thousands of machine-specific files. Ignore it in Git (L04).
- Creating a venv inside another one, or using `sudo` with pip.
- Moving or renaming the project folder and expecting `.venv` to keep working. Recreate it instead.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "What should go into Git for a Python project?",
  "options": ["The .venv/ folder", "requirements.txt", "Both", "Neither"], "answer": 1,
  "explanation": "Commit the recipe (requirements.txt), not the cooked environment. Anyone can rebuild .venv from it." }
```

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "You renamed your project folder. Now `.venv/bin/pip` fails with `bad interpreter: .../old-name/.venv/bin/python3: no such file or directory`. What's the best fix?",
  "options": ["Delete .venv, recreate it and reinstall from requirements.txt", "Edit the paths inside .venv/bin by hand", "Install the packages system-wide instead", "Run it with sudo"], "answer": 0,
  "explanation": "Scripts in .venv/bin hard-code the absolute path of the venv's interpreter. Venvs aren't movable: recreate them, which is why requirements.txt exists." }
```

## 5. Try it (5 minutes, nothing to submit)

In an empty scratch folder:

1. `python3 -m venv .venv`
2. `.venv/bin/python -c "import sys; print(sys.executable)"`. The path ends in `.venv/bin/python`.
3. `python3 -m pip install iniconfig`. Read the refusal.
4. `.venv/bin/python -m pip install iniconfig`, then `.venv/bin/python -m pip freeze`.
5. Delete `.venv`, recreate it, and reinstall from a `requirements.txt` you froze.

```quiz
{ "id": "q5", "type": "explain", "label": "Explain",
  "prompt": "In your own words: what does the 'externally-managed-environment' error protect, and what's the right response?",
  "model": "It protects the operating system's own Python packages, which the OS package manager owns, from being changed by pip. The right response is to create a venv and install there, not to force it with --break-system-packages.",
  "explanation": "The system's Python belongs to the OS. Your project's dependencies belong in the project's venv." }
```
