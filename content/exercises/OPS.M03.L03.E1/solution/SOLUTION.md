```yaml
default:
  image: python:3.12-slim
  cache:
    key:
      files:
        - requirements.txt
    paths:
      - .cache/pip
  before_script:
    - python -m pip install -r requirements.txt

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

stages:
  - check

lint:
  stage: check
  script:
    - ruff check .
    - ruff format --check .

test:
  stage: check
  script:
    - pytest -q
```

**Why it works**

- **`default:`** holds what every job shares: the image, the cache and the install. Top-level `cache` and `before_script` are deprecated in favour of `default:`. A job that sets one of these keywords itself replaces the default for that keyword (no merging).
- **`python:3.12-slim`** matches the Python of the app's Dockerfile (OPS.M01). `latest` would move to a new Python without anyone changing the repository.
- **The secret is gone.** Variables in `.gitlab-ci.yml` are visible to everyone with repository access. Add `OAUTH_CLIENT_SECRET` under Settings > CI/CD > Variables as **masked** (hidden as `[MASKED]` in job logs; the value must be at least 8 characters, on a single line) and **protected** if only protected branches should get it. And rotate it: the old value stays in Git history.
- **Pip cache.** pip reads options from `PIP_<OPTION>` environment variables, so `PIP_CACHE_DIR` works like `--cache-dir`. GitLab can only cache paths inside the project directory, which is why it points into `$CI_PROJECT_DIR`. `key: files: [requirements.txt]` gives the cache a new key whenever requirements change.
- **One check per script line.** GitLab fails the job at the first script command that exits non-zero, but when several commands share one line, only the last one's result counts: in the old `ruff check . ; ruff format --check . ; pytest`, lint and format failures were invisible whenever pytest passed.
- Both jobs are in one stage, so they run in parallel.

**Alternatives**

- Ruff's integrations page shows a GitLab job using the `ghcr.io/astral-sh/ruff` image with `--output-format=gitlab` and a code-quality report. That's faster (no pip install), but then the Ruff version lives in the image tag instead of requirements.txt.
- `workflow: rules:` can limit pipelines to branches and merge requests and avoid duplicate pipelines.
