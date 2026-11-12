---
{
  "id": "OPS.M03.L02",
  "title": "GitHub Actions: a workflow that runs Ruff and pytest",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["OPS.M03.L01"],
  "objectives": [
    "Read and write a GitHub Actions workflow: on, jobs, runs-on, steps with uses and run",
    "Build a job that checks out code, sets up a pinned Python with pip caching, installs requirements.txt and runs ruff check, ruff format --check and pytest",
    "Explain why a non-zero exit code fails the step and the job, and why separate steps help",
    "Avoid YAML traps in workflows: unquoted versions and the `on` key",
    "Use repository secrets instead of values in the workflow file"
  ],
  "why": "CI turns 'it works on my machine' into 'it works on a clean machine, on every push'. You've run Ruff and pytest locally; a workflow runs the same commands automatically and blocks a merge when they fail. Your company uses GitLab CI (next lesson), but many open-source projects and job-interview take-home repos use GitHub Actions, and the concepts carry over one to one.",
  "applications": [
    "A required status check that blocks merging a pull request with failing tests",
    "Catching an unformatted file or an unused import before a reviewer has to",
    "Reproducing CI failures locally because the workflow runs the same commands you do"
  ],
  "exercises": ["OPS.M03.L02.E1"],
  "sources": [
    {
      "title": "Workflow syntax for GitHub Actions",
      "url": "https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax",
      "version": "GitHub Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": [
        "Workflow files live in .github/workflows and use .yml or .yaml",
        "on defines triggering events; runs-on selects the runner",
        "Jobs run in parallel by default; needs makes them sequential",
        "A job is a sequence of steps; uses selects an action, run runs shell commands, with passes inputs; each step runs in its own process",
        "Default bash shell runs with -e (fail fast); explicit bash adds -o pipefail",
        "Pin actions to a version (Git ref, SHA or tag); a commit SHA is safest",
        "permissions limits GITHUB_TOKEN; timeout-minutes maximum 360"
      ]
    },
    {
      "title": "Events that trigger workflows",
      "url": "https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows",
      "version": "GitHub Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["push runs when you push a commit or tag", "pull_request runs by default for opened, synchronize and reopened", "workflow_dispatch enables manual runs"]
    },
    {
      "title": "actions/setup-python (README)",
      "url": "https://github.com/actions/setup-python",
      "version": "setup-python v7, as shown in the README on 2026-11-12",
      "verified": "2026-11-12",
      "claims": ["Usage example uses actions/setup-python@v7 with python-version", "cache: 'pip' is optional and off by default; it looks for requirements.txt or pyproject.toml and caches pip's global cache directory"]
    },
    {
      "title": "actions/checkout (README)",
      "url": "https://github.com/actions/checkout",
      "version": "checkout v7, as shown in the README on 2026-11-12",
      "verified": "2026-11-12",
      "claims": ["Usage example uses actions/checkout@v7", "fetch-depth defaults to 1 (one commit)"]
    },
    {
      "title": "Building and testing Python",
      "url": "https://docs.github.com/en/actions/tutorials/build-and-test-code/python",
      "version": "GitHub Docs (current; examples there use checkout@v6 and setup-python@v5)",
      "verified": "2026-11-12",
      "claims": ["setup-python is the recommended way to use Python in Actions", "Install from requirements.txt with pip; versions are written quoted, e.g. '3.12'", "strategy.matrix can test several Python versions"]
    },
    {
      "title": "GitHub-hosted runners",
      "url": "https://docs.github.com/en/actions/reference/runners/github-hosted-runners",
      "version": "GitHub Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Linux labels include ubuntu-latest, ubuntu-24.04, ubuntu-22.04 and ubuntu-26.04"]
    },
    {
      "title": "Using secrets in GitHub Actions",
      "url": "https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets",
      "version": "GitHub Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Secrets are read with the secrets context, e.g. ${{ secrets.NAME }}, and passed to a step via env", "Secrets (except GITHUB_TOKEN) are not passed to the runner for workflows triggered from a forked repository"]
    },
    {
      "title": "Ruff integrations (GitHub Actions)",
      "url": "https://docs.astral.sh/ruff/integrations/",
      "version": "Ruff docs (current); installed ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": ["ruff check --output-format=github produces GitHub annotations"]
    }
  ]
}
---
*GitHub Actions can't run on this machine. The workflow files below are not run here, and their behaviour is as described in the cited GitHub docs. The commands inside them (Ruff, pytest) are real local runs.*

## 1. The model: events, jobs, steps

A workflow is a YAML file in `.github/workflows/`. Its anatomy:

- **`on:`** names the events that start it, e.g. `push` (a commit or tag was pushed) or `pull_request`.
- **`jobs:`** are separate units of work. Each runs on a fresh virtual machine, the **runner**, chosen with `runs-on:` (e.g. `ubuntu-24.04`). Jobs run **in parallel** unless one `needs:` another.
- **`steps:`** run in order inside a job. A step either **`uses:`** an action (reusable code, like `actions/checkout`) with inputs under `with:`, or **`run:`**s shell commands.

**A step fails when its command exits non-zero, and then the job fails.** That's the same exit-code contract as Ruff (1 on findings) and pytest. GitHub's default bash shell also runs with `-e`, so a multi-line `run:` stops at its first failing command.

Here are the three commands a Python job runs, executed locally on a tiny project:

```console
$ ruff check .
All checks passed!
$ ruff format --check .
2 files already formatted
$ pytest -q
..                                                                       [100%]
2 passed in 0.00s
```

And after breaking `word_count` (`split(" ")` instead of `split()`):

```console
$ pytest -q
...
FAILED test_notes.py::test_counts_words - AssertionError: assert 3 == 2
FAILED test_notes.py::test_empty - AssertionError: assert 1 == 0
2 failed in 0.01s
$ echo $?
1
```

On a runner, that exit code 1 turns the step red, the job red and the pull request's check red.

```quiz
{ "id": "q1", "type": "truefalse",
  "prompt": "Two jobs in the same workflow, `lint` and `test`, run one after the other in the order they're written.", "answer": false,
  "explanation": "Jobs run in parallel by default, each on its own fresh runner. Use needs: [lint] on test if it should wait." }
```

## 2. A workflow for a Python service

Here's a workflow for the notes service from earlier modules. It uses two parallel jobs and named steps, so the GitHub UI shows readable labels:

```yaml
name: checks

on: [push, pull_request]

permissions:
  contents: read

jobs:
  lint:
    runs-on: ubuntu-24.04
    steps:
      - name: Check out the repository
        uses: actions/checkout@v7
      - name: Set up Python
        uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip
      - name: Install dependencies
        run: python -m pip install -r requirements-dev.txt
      - name: Lint
        run: ruff check --output-format=github .
      - name: Formatting
        run: ruff format --check .

  test:
    runs-on: ubuntu-24.04
    steps:
      - name: Check out the repository
        uses: actions/checkout@v7
      - name: Set up Python
        uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip
      - name: Install dependencies
        run: python -m pip install -r requirements-dev.txt
      - name: Tests
        run: pytest -q
```

What each part buys you:

- **`actions/checkout` first.** A runner starts with an empty workspace. Without checkout there is no code to lint. (By default it fetches just one commit, which is all a lint and test job needs.)
- **`actions/setup-python`** installs the requested Python. GitHub calls it the recommended way to get Python on a runner. Match the version your Docker image uses (OPS.M01), here 3.12.
- **`cache: pip`** is off by default. Turned on, setup-python caches pip's global cache directory between runs, finding your requirements file automatically. It speeds up downloads; the install step still runs.
- **Pinned actions**: `@v7` is the major version both actions' READMEs currently show. GitHub's docs call a full commit SHA the safest pin, because tags can move (the same idea as base-image tags in OPS.M01).
- **`permissions: contents: read`** gives the job's automatic `GITHUB_TOKEN` only read access, because lint and tests don't need more.
- **`--output-format=github`** makes Ruff print findings as annotations that GitHub shows on the changed lines.
- **Each check is its own step**, so a red step tells you *which* check failed. Splitting lint and tests into two jobs also means a lint failure can't hide the test result: the jobs run in parallel and report separately.

```quiz
{ "id": "q2", "type": "choice", "label": "Debugging",
  "prompt": "A job's first step is `- run: pip install -r requirements.txt` and it fails with `No such file or directory: 'requirements.txt'`. The file is in the repository root. What's missing?",
  "options": ["An actions/checkout step before it", "A cache: pip setting", "runs-on: ubuntu-latest", "A needs: entry"], "answer": 0,
  "explanation": "The runner's workspace is empty until actions/checkout clones the repository into it." }
```

## 3. YAML traps in workflow files

Two traps catch everyone once. Both come from YAML 1.1 rules, which PyYAML (and the tests in this module) follow:

```quiz
{ "id": "q3", "type": "output",
  "prompt": "What does this print?",
  "code": "import yaml\nprint(yaml.safe_load('python-version: 3.10'))\nprint(yaml.safe_load('python-version: \"3.10\"'))",
  "answer": "{'python-version': 3.1}\n{'python-version': '3.10'}",
  "explanation": "Unquoted, 3.10 is the float 3.1, so setup-python would be asked for Python 3.1. Always quote versions: \"3.12\"." }
```

```quiz
{ "id": "q4", "type": "output",
  "prompt": "PyYAML follows YAML 1.1, where `on` is a boolean word. What does this print?",
  "code": "import yaml\nprint(yaml.safe_load('on: [push, pull_request]'))",
  "answer": "{True: ['push', 'pull_request']}",
  "explanation": "The key on becomes the boolean True. GitHub reads it as the on key, but any Python tool that checks workflows with PyYAML must look up data.get(\"on\", data.get(True)). The exercise's tests do exactly that." }
```

## 4. Secrets in workflows

Tests sometimes need a credential, such as a token for a private package index. It never goes into the YAML file, because anyone who can read the repository can read the file. Store it as a repository secret in the settings, then pass it to the one step that needs it:

```yaml
      - name: Install private packages
        env:
          INDEX_TOKEN: ${{ secrets.INDEX_TOKEN }}
        run: python -m pip install --index-url "https://__token__:${INDEX_TOKEN}@pypi.example.com/simple" -r requirements.txt
```

- `${{ secrets.NAME }}` reads from the `secrets` context. Expose it as an environment variable (OPS.M02: config from the environment) only on the step that needs it.
- Workflows triggered from a **fork** don't receive your secrets (apart from `GITHUB_TOKEN`), so a stranger's pull request can't simply print them.
- Never `echo` a secret to debug. Treat CI logs as public.

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "Where does a test-only API key for a sandbox service belong?",
  "options": ["A repository secret, passed via env: to the test step", "The env: block at the top of ci.yml, since it's only a sandbox key", "requirements.txt", "A comment in the workflow so others can find it"], "answer": 0,
  "explanation": "Even sandbox keys get abused, and workflow files are readable by everyone with repository access. Secrets go in the secret store and reach only the steps that need them." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "CI passes, but a teammate's laptop shows 12 Ruff findings on the same commit. Name two likely causes and how the workflow and repository should prevent them.",
  "model": "Different Ruff versions (the default rule set and the rules themselves change), or a different configuration (no explicit select, or the laptop's ruff isn't reading the repo's pyproject.toml). Fix: pin ruff in requirements.txt, install it in CI with pip install -r requirements.txt, and set [tool.ruff.lint] select explicitly in pyproject.toml.",
  "explanation": "CI is only a gate if it runs the same tool versions and config as developers." }
```

## 5. Your turn

The exercise's `ci.yml` only runs when started by hand, skips checkout, asks for the wrong Python and runs only pytest. Make it run on every push with checkout, Python 3.12, a pip cache, the install, and the three checks. The tests parse the YAML; in a real repository the file would live at `.github/workflows/ci.yml`.

```exercise
OPS.M03.L02.E1
```
