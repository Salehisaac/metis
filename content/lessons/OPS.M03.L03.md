---
{
  "id": "OPS.M03.L03",
  "title": "GitLab CI: .gitlab-ci.yml, caching and CI secrets",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["OPS.M03.L02"],
  "objectives": [
    "Map GitHub Actions concepts to GitLab CI: pipeline, stages, jobs, image, script, before_script, default",
    "Write a .gitlab-ci.yml that runs ruff check, ruff format --check and pytest in a pinned Python image",
    "Cache pip downloads correctly: PIP_CACHE_DIR inside the project and a cache key based on requirements.txt",
    "Explain why each check needs its own script line",
    "Keep secrets out of .gitlab-ci.yml with masked and protected CI/CD variables, and know the limits of masking"
  ],
  "why": "Your company's pipelines are .gitlab-ci.yml files. Knowing exactly what each keyword does lets you read the existing pipeline, spot when a check can't actually fail, and add a Python service's checks without copying a template you don't understand.",
  "applications": [
    "Adding Ruff and pytest jobs to an existing GitLab pipeline at work",
    "Speeding up slow pipelines with a correct pip cache",
    "Moving a secret from .gitlab-ci.yml to a masked, protected variable"
  ],
  "exercises": ["OPS.M03.L03.E1"],
  "sources": [
    {
      "title": "CI/CD YAML syntax reference",
      "url": "https://docs.gitlab.com/ci/yaml/",
      "version": "GitLab Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": [
        "image specifies the Docker image the job runs in; script lists commands for the runner; all jobs except trigger jobs require script",
        "stages group jobs; default stages .pre, build, test, deploy, .post; jobs in the same stage run in parallel",
        "before_script runs before each job's script",
        "default accepts after_script, artifacts, before_script, cache, image, interruptible, retry, services, tags...; a job keyword replaces the default (no merging); top-level cache and before_script are deprecated in favour of default",
        "cache paths are relative to $CI_PROJECT_DIR and must be in the working copy; cache:key:files creates a new key when the files change",
        "variables defined in a job take precedence over default variables"
      ]
    },
    {
      "title": "CI/CD pipelines",
      "url": "https://docs.gitlab.com/ci/pipelines/",
      "version": "GitLab Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Pipelines are configured in .gitlab-ci.yml and can run automatically for events such as pushes", "Jobs in a stage run in parallel and stages run in sequence; if any job in a stage fails, the next stage is usually not executed"]
    },
    {
      "title": "script keyword: exit codes",
      "url": "https://docs.gitlab.com/ci/yaml/script/",
      "version": "GitLab Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["A non-zero exit code fails the job and further commands don't run", "If several commands are combined into one command string, only the last command's result is reported; use separate script items"]
    },
    {
      "title": "Caching in GitLab CI/CD",
      "url": "https://docs.gitlab.com/ci/caching/",
      "version": "GitLab Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Use cache for dependencies downloaded from the internet; artifacts pass build results between stages", "Cache paths are relative to the project directory"]
    },
    {
      "title": "workflow keyword",
      "url": "https://docs.gitlab.com/ci/yaml/workflow/",
      "version": "GitLab Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Example workflow rules running branch and merge request pipelines while avoiding duplicates with CI_OPEN_MERGE_REQUESTS"]
    },
    {
      "title": "Job rules: CI_PIPELINE_SOURCE values",
      "url": "https://docs.gitlab.com/ci/jobs/job_rules/",
      "version": "GitLab Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["CI_PIPELINE_SOURCE is push for Git pushes (branches and tags) and merge_request_event when a merge request is created or updated"]
    },
    {
      "title": "Merge request pipelines",
      "url": "https://docs.gitlab.com/ci/pipelines/merge_request_pipelines/",
      "version": "GitLab Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Jobs must be configured to run in merge request pipelines, per job with rules or for all jobs with workflow:rules matching merge_request_event"]
    },
    {
      "title": "Predefined CI/CD variables",
      "url": "https://docs.gitlab.com/ci/variables/predefined_variables/",
      "version": "GitLab Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["CI_PROJECT_DIR is the full path the repository is cloned to, and where the job runs from"]
    },
    {
      "title": "GitLab CI/CD variables",
      "url": "https://docs.gitlab.com/ci/variables/",
      "version": "GitLab Docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Variables in .gitlab-ci.yml are visible to everyone with repository access; sensitive values go in the UI", "Masked variables show as [MASKED] in job logs; values must be single-line and at least 8 characters", "Masking is not a guaranteed protection", "Protected variables are only available to pipelines on protected branches or tags"]
    },
    {
      "title": "pip: Configuration (environment variables)",
      "url": "https://pip.pypa.io/en/stable/topics/configuration/",
      "version": "pip docs (stable); installed pip 24.0",
      "verified": "2026-11-12",
      "claims": ["pip options can be set as environment variables PIP_<UPPER_LONG_NAME>, with dashes replaced by underscores"]
    },
    {
      "title": "Ruff integrations (GitLab CI/CD)",
      "url": "https://docs.astral.sh/ruff/integrations/",
      "version": "Ruff docs (current; its example image tag is 0.17.4, installed ruff is 0.17.3)",
      "verified": "2026-11-12",
      "claims": ["GitLab example using the ghcr.io/astral-sh/ruff image, ruff check --output-format=gitlab with a code-quality report"]
    }
  ]
}
---
*GitLab runners aren't available on this machine. The pipeline files here are not run, and their behaviour is as described in the cited GitLab docs. Shell and pip snippets are real local runs.*

## 1. Same ideas, different words

You already know the GitHub version. Here's the translation:

| GitHub Actions | GitLab CI |
|---|---|
| `.github/workflows/*.yml` | one `.gitlab-ci.yml` per project |
| `on:` | pipelines run for pushes by default; `workflow: rules:` narrows it |
| job with `runs-on:` | **job** = any top-level key that isn't a keyword; it runs in a Docker **`image:`** |
| `steps:` with `run:` | **`script:`**, a list of shell commands (required in every normal job) |
| jobs parallel unless `needs:` | **stages** run in order; jobs **in the same stage run in parallel** |
| `actions/checkout` | not needed: the runner clones the repo into `$CI_PROJECT_DIR` first |
| setup-python | choose a Python image, e.g. `python:3.12-slim` (OPS.M01's base) |
| repository secrets | **CI/CD variables** in project settings, masked and/or protected |

**`before_script`** runs before each job's `script`, and **`default:`** sets keywords (image, cache, before_script, ...) for every job. A job that sets the same keyword *replaces* the default; nothing is merged. Top-level `cache` and `before_script` still work but are deprecated in favour of `default:`.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "A pipeline has `stages: [lint, test]`. Jobs `ruff` and `format` are in lint; `pytest` is in test. How do they run?",
  "options": ["ruff and format in parallel; pytest after both succeed", "All three in parallel", "ruff, then format, then pytest", "pytest first, because test is the default stage"], "answer": 0,
  "explanation": "Stages run in sequence and jobs within a stage run in parallel. If a lint job fails, the test stage usually doesn't start and the pipeline ends early." }
```

## 2. A pipeline for a Python service

Here is the notes service's pipeline:

```yaml
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS
      when: never
    - if: $CI_COMMIT_BRANCH

default:
  image: python:3.12.16-slim
  cache:
    key:
      files:
        - requirements-dev.txt
    paths:
      - .pip-cache/
  before_script:
    - python -m pip install -r requirements-dev.txt

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.pip-cache"

stages:
  - lint
  - test

ruff-lint:
  stage: lint
  script:
    - ruff check --output-format=gitlab --output-file=code-quality-report.json .

ruff-format:
  stage: lint
  script:
    - ruff format --check --diff .

unit-tests:
  stage: test
  script:
    - pytest -q
```

Reading it top to bottom:

- **`workflow: rules:`** is GitLab's documented recipe for "run branch pipelines and merge request pipelines, but not both for the same push". `CI_PIPELINE_SOURCE` is `push` for a Git push and `merge_request_event` for merge requests. Per GitLab's merge request pipeline docs, workflow rules that match `merge_request_event` make *all* jobs run in merge request pipelines, so the jobs here need no `rules:` of their own. Without a `workflow:` block at all, a push simply starts a branch pipeline, which is all the exercise needs.
- **`default:`** gives every job the same pinned image, the cache and the install.
- **`--output-format=gitlab`** writes Ruff's findings as a code-quality report, as in Ruff's own GitLab example (which also uploads it as an artifact). `--check --diff` shows *what* would change and still exits 1.
- **Separate jobs** show up as separate boxes in the pipeline view, so you see at a glance which check failed.

## 3. One check per script line

GitLab fails the job as soon as a `script` command exits non-zero, and stops running further commands. But GitLab's docs describe a trap (a known runner issue): **if several commands are combined into one line, only the last one's result is reported**. Plain shell behaviour makes it easy to remember, because in a shell without `-e`, `;` runs the next command and the line keeps the last exit status:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "`false` always exits 1, and `true` always exits 0. What does this print?",
  "code": "import subprocess\nr = subprocess.run(\"false ; true\", shell=True)\nprint(r.returncode)",
  "answer": "0",
  "explanation": "In a plain shell, the line's status is the last command's status. GitLab documents the same outcome for combined script lines: in `ruff check . ; pytest`, a lint failure disappears whenever pytest passes. Put each check on its own script line." }
```

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "`- ruff check . && pytest` as one script line is as safe as two separate lines.", "answer": false,
  "explanation": "With &&, a Ruff failure stops the line before pytest runs, so you learn about only one problem per pipeline, and the log mixes two checks in one command. GitLab's docs also say that for combined commands only the last command's result is reported, and recommend separate script items." }
```

## 4. Caching pip downloads

Each job starts from a fresh container, so `pip install` downloads everything again unless you cache pip's download cache. Two rules from GitLab's docs shape the setup:

1. **Cache paths must be inside the project directory** (`$CI_PROJECT_DIR`). pip's default cache on Linux, `~/.cache/pip`, is outside it, so it can't be cached as is.
2. pip reads any option from an environment variable named **`PIP_<OPTION>`**, so `PIP_CACHE_DIR` does the same as `--cache-dir`:

```console
$ PIP_CACHE_DIR=/builds/notes/.pip-cache pip cache dir
/builds/notes/.pip-cache
```

(Run locally with pip 24.0; the path is just an example.) Then:

- `cache: paths:` lists that folder, so GitLab saves and restores it between pipelines.
- `cache: key: files: [requirements-dev.txt]` gives the cache a new key whenever the requirements change, so a new dependency set starts a fresh cache instead of reusing a stale one.
- The install still runs every time; it just reads packages from the cache instead of downloading them.

**Cache vs. artifacts**: a cache holds dependencies you could re-download, and is a speed-up only. Artifacts carry results you need later in the pipeline (reports, built files). Never rely on a cache being present.

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "A pipeline caches `paths: [/root/.cache/pip]`, and every job still downloads all packages. Why?",
  "options": ["Cache paths must be inside the project directory; set PIP_CACHE_DIR under $CI_PROJECT_DIR and cache that", "pip doesn't use a cache in containers", "The cache key must be latest", "Caches only work in the build stage"], "answer": 0,
  "explanation": "GitLab caches only paths relative to $CI_PROJECT_DIR, inside the working copy. Point pip's cache there and list that path." }
```

## 5. Secrets in GitLab CI

`variables:` in `.gitlab-ci.yml` is fine for non-secret config such as `PIP_CACHE_DIR`. It's the wrong place for secrets, because **variables in the file are visible to everyone with repository access**, and they stay in Git history. Put them in **Settings > CI/CD > Variables** instead:

- **Masked**: if a job prints the value, the log shows `[MASKED]`. The value must be a single line of at least 8 characters. GitLab is explicit that masking is *not* a guarantee: a script can still transform and leak a value.
- **Protected**: the variable exists only in pipelines for protected branches or tags, so a feature branch can't read the production deploy key.
- Jobs receive them as ordinary environment variables, which is exactly what your `load_settings(os.environ)` from OPS.M02 reads.

This is where a hardcoded OAuth secret should have lived: a masked, protected variable, read from the environment at startup, never in source.

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "A colleague adds `variables: DEPLOY_TOKEN: \"glpat-...\"` to .gitlab-ci.yml, saying 'the repo is internal'. What do you recommend?",
  "options": ["Rotate the token, delete it from the file and add it as a masked, protected CI/CD variable", "Mark the line with a comment so nobody copies it", "Move it into before_script", "Base64-encode it in the file"], "answer": 0,
  "explanation": "Anyone with repository access can read the file and its history, so the token is already exposed and needs rotating. Project CI/CD variables keep it out of the repository; protected limits it to protected branches. Encoding isn't encryption." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "You're adding a Python service to your company's GitLab. In four bullets, describe its .gitlab-ci.yml: image, install and cache, the checks, and secrets.",
  "model": "Image: python:3.12-slim (matching the Dockerfile) in default:. Install: before_script python -m pip install -r requirements.txt, with PIP_CACHE_DIR under $CI_PROJECT_DIR and cache key files: requirements.txt. Checks: ruff check, ruff format --check and pytest on separate script lines or in separate jobs, with stages for order. Secrets: masked/protected CI/CD variables read via os.environ, nothing secret in the file.",
  "explanation": "Pinned environment, reproducible install, checks that can each fail the pipeline, and secrets outside the repository." }
```

## 6. Your turn

The team's `.gitlab-ci.yml` uses `python:latest`, commits a secret, never caches pip and runs all three checks on one line. Fix all four. The tests parse the YAML.

```exercise
OPS.M03.L03.E1
```
