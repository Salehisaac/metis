```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  checks:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install -r requirements.txt
      - run: ruff check .
      - run: ruff format --check .
      - run: pytest -q
```

**Why it works**

- **`on: push`** runs the workflow whenever you push a commit or tag; `pull_request` adds runs when a pull request is opened, updated (synchronize) or reopened. `workflow_dispatch` alone only enables manual runs.
- **Checkout first.** The runner's workspace starts empty; without `actions/checkout` there is no requirements.txt and no code. Actions are pinned to a major version tag (`@v7`, the version their READMEs show); GitHub's docs call a full commit SHA the safest pin.
- **`python-version: "3.12"` quoted.** Unquoted, YAML reads `3.10` as the float 3.1, the classic "why is CI on Python 3.1" bug. 3.12 matches the Docker image (OPS.M01) and your venv.
- **`cache: pip`** makes setup-python cache pip's global cache directory (it looks for requirements.txt by default), so later runs download less. The install step still runs every time.
- **One check per step.** The default shell runs with `-e`, so a step stops at its first failing command. Separate steps show exactly which check failed, and each step's exit code fails the job.
- `python -m pip` ties pip to the Python that setup-python installed (PY.M01).

**Alternatives**

- Two jobs, `lint` and `test`, run in parallel by default and report separately; each repeats checkout, setup and install.
- `ruff check --output-format=github .` turns findings into annotations on the changed lines (Ruff's integrations page).
- A `strategy.matrix` over several Python versions is useful for libraries; an application usually tests the one version it deploys.
