---
{ "id": "OPS.M03.A", "module": "OPS.M03", "title": "OPS.M03 module assessment: Ruff and CI pipelines", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before moving on.

```quiz
{ "id": "a1", "type": "choice",
  "prompt": "Which command belongs in CI to enforce formatting?",
  "options": ["ruff format --check .", "ruff format .", "ruff check --exit-zero .", "ruff check --fix ."], "answer": 0,
  "explanation": "--check writes nothing and exits 1 if a file would change, so the job fails. ruff format and --fix change files on the runner and pass; --exit-zero can never fail." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "A tool loads a workflow file with PyYAML. What does this print?",
  "code": "import yaml\ndoc = yaml.safe_load('on: push\\npython-version: 3.10')\nprint(sorted(doc.items(), key=str))",
  "answer": "[('python-version', 3.1), (True, 'push')]",
  "explanation": "In YAML 1.1 the bare key on is the boolean True, and the unquoted 3.10 is the float 3.1. Quote versions in CI files, and look up True as well as \"on\" when you parse workflows in Python." }
```

```quiz
{ "id": "a3", "type": "choice", "label": "Debugging",
  "prompt": "A GitLab job's script is `- ruff check . ; pytest`. Ruff reports 5 findings, pytest passes. What's the job status?",
  "options": ["Passed: only the last command's result counts for a combined line", "Failed: Ruff exited 1", "Failed with a warning", "Skipped"], "answer": 0,
  "explanation": "GitLab's docs say that when commands are combined into one script line, only the last command's result is reported, here pytest's 0 (the same as a plain shell, where ; keeps the last exit status). Use one command per script item so each can fail the job." }
```

```quiz
{ "id": "a4", "type": "truefalse",
  "prompt": "In GitHub Actions, two jobs in the same workflow run in parallel unless one declares `needs:` on the other.", "answer": true,
  "explanation": "Jobs run in parallel by default on separate runners. In GitLab, the equivalent ordering tool is stages (jobs in a stage run in parallel; stages run in sequence)." }
```

```quiz
{ "id": "a5", "type": "choice",
  "prompt": "CI fails on `B006 Do not use mutable data structures for argument defaults`. What's the best response?",
  "options": ["Use None as the default and create the list inside the function", "Add # noqa: B006", "Remove B from select in pyproject.toml", "Run ruff check --fix --unsafe-fixes in CI"], "answer": 0,
  "explanation": "The default list is created once and shared by every call, a real aliasing bug. Silencing the rule hides it, and auto-applying unsafe fixes in CI changes code nobody reviewed." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Your GitLab pipeline takes 6 minutes, mostly `pip install`, and has `PIP_CACHE_DIR` unset and `cache: paths: [~/.cache/pip]`. What do you change, and why does the old setup not work?",
  "model": "GitLab only caches paths inside $CI_PROJECT_DIR, and ~/.cache/pip is outside it, so nothing is saved. Set variables: PIP_CACHE_DIR: \"$CI_PROJECT_DIR/.cache/pip\" (pip reads PIP_<OPTION> env vars), cache paths: [.cache/pip] with key: files: [requirements.txt] so the cache renews when dependencies change. The install still runs but reads from the cache.",
  "explanation": "Cache location rules plus a key tied to the dependency file." }
```
