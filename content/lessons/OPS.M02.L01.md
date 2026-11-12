---
{
  "id": "OPS.M02.L01",
  "title": "Configuration from the environment: 12-factor and secrets",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["OPS.M01"],
  "objectives": [
    "Apply the 12-factor rule: config that varies between deploys comes from environment variables, never from code",
    "Read os.environ correctly: values are strings, missing keys raise KeyError, and .get defaults keep their own type",
    "Build a frozen, typed settings object at startup that validates every value and fails fast with one clear error",
    "Keep secrets out of code, Git, reprs and error messages, and know what to do when one leaks"
  ],
  "why": "A hardcoded OAuth secret once shipped in source code. Deleting it later didn't un-ship it: it stayed in Git history and in every build made before the fix. Reading config from the environment, typed and validated in one place, makes that mistake structurally hard and makes the same image runnable in dev, CI and production.",
  "applications": [
    "One Docker image promoted unchanged from staging to production with different environment variables",
    "Startup that crashes immediately with 'missing DATABASE_URL' instead of failing on the first request",
    "Code reviews that catch secrets, magic hostnames and DEBUG flags in source"
  ],
  "exercises": ["OPS.M02.L01.E1"],
  "sources": [
    {
      "title": "The Twelve-Factor App: III. Config",
      "url": "https://12factor.net/config",
      "version": "12factor.net (current)",
      "verified": "2026-11-12",
      "claims": ["Config is everything likely to vary between deploys, including credentials and backing-service handles", "Strict separation of config from code; litmus test: could the codebase be open-sourced without compromising credentials", "Store config in environment variables: language- and OS-agnostic, unlikely to be committed", "Named environment groups don't scale; env vars are granular, orthogonal controls"]
    },
    {
      "title": "The Twelve-Factor App: IV. Backing services",
      "url": "https://12factor.net/backing-services",
      "version": "12factor.net (current)",
      "verified": "2026-11-12",
      "claims": ["Backing services are attached resources accessed via a URL or locator stored in config, swappable without code changes"]
    },
    {
      "title": "os: os.environ and os.getenv",
      "url": "https://docs.python.org/3.12/library/os.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["os.environ is a mapping of strings representing the process environment", "It is captured when os is first imported; later outside changes aren't reflected", "os.getenv(key, default=None) returns the value as a string or the default"]
    },
    {
      "title": "dataclasses: field(repr=...) and frozen",
      "url": "https://docs.python.org/3.12/library/dataclasses.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["field(repr=False) excludes a field from the generated __repr__", "frozen=True makes assigning to fields raise FrozenInstanceError"]
    },
    {
      "title": "FastAPI: Settings and Environment Variables",
      "url": "https://fastapi.tiangolo.com/advanced/settings/",
      "version": "FastAPI docs (current; installed fastapi 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Values read from environment variables are str; conversion and validation must be done in code", "pydantic-settings is a separate package providing BaseSettings, which reads env vars case-insensitively and validates them", ".env support needs python-dotenv", "A get_settings dependency wrapped in lru_cache creates the settings once"]
    }
  ]
}
---
## 1. Config is whatever changes between deploys

The [Twelve-Factor App](https://12factor.net/config) defines config as *everything that is likely to vary between deploys*: database URLs, Redis hosts, credentials for outside services like OAuth providers, feature flags, the log level. Its rule is **strict separation of config from code**, and its litmus test is blunt:

> Could you open-source the codebase right now without compromising any credentials?

A hardcoded OAuth client secret fails that test, and so does a `config/prod.yaml` with a password in it. The twelve-factor answer is **environment variables**:

- They change per deploy without changing code, so you build **one image** (OPS.M01) and run it everywhere.
- They're language- and OS-agnostic. Compose's `environment:`, CI variables and Kubernetes all speak them.
- They're unlikely to be committed by accident, unlike config files.

It also argues against grouping config into named environments (`development`, `staging`, `prod`) inside the app: every new deploy multiplies the combinations. Each variable is an independent knob.

In Go you'd reach for `os.Getenv`. In Python it's `os.environ`, with a few traps.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "Which of these belongs in the environment rather than in the code?",
  "options": ["The Redis URL", "The list of API routes", "The bcrypt work factor that every deploy must share", "The name of the Pydantic model for orders"], "answer": 0,
  "explanation": "The Redis URL differs between your laptop, CI and production. Twelve-factor calls backing services attached resources whose locators live in config. Routes and model names are code: identical in every deploy." }
```

## 2. `os.environ`: everything is a string

`os.environ` is a mapping of **strings**, captured when Python starts. Three consequences:

```python
import os

os.environ["NOPE_NOT_SET"]          # KeyError: 'NOPE_NOT_SET'
os.environ.get("PORT")              # None if unset, else a str like '8080'
os.environ["PORT"] = 8080           # TypeError: str expected, not int
```

The type surprise comes from `.get` with a non-string default:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import os\nos.environ[\"PORT\"] = \"8080\"\nprint(type(os.environ.get(\"PORT\", 8000)).__name__)\ndel os.environ[\"PORT\"]\nprint(type(os.environ.get(\"PORT\", 8000)).__name__)",
  "answer": "str\nint",
  "explanation": "When PORT is set you get its string value; when it isn't you get your default, an int. Code that does port + 1 works on your laptop and crashes in production. Convert explicitly, in one place." }
```

Booleans are worse, because every non-empty string is truthy:

```quiz
{ "id": "q3", "type": "output",
  "prompt": "A colleague writes `debug = bool(os.environ.get(\"DEBUG\", \"\"))`. With DEBUG=false, what is debug? This mirrors it:",
  "code": "print(bool(\"false\"), bool(\"0\"), bool(\"\"))",
  "answer": "True True False",
  "explanation": "bool() of a string only checks for emptiness. DEBUG=false turns debug mode ON. Parse an explicit set of words instead." }
```

## 3. One typed settings object, validated at startup

Scattered `os.environ.get(...)` calls spread conversions, defaults and typos all over the codebase. Read everything **once, at startup**, into one typed object, and crash immediately if it's wrong. Here it is for a mail-sending service (a different app from the exercise's):

```python
from dataclasses import dataclass, field


class BadConfig(Exception):
    pass


@dataclass(frozen=True)
class MailerConfig:
    smtp_host: str
    api_key: str = field(repr=False)
    timeout_seconds: float = 10.0


def read_mailer_config(environ):
    problems = [name for name in ("SMTP_HOST", "MAILER_API_KEY") if not environ.get(name, "").strip()]
    if problems:
        raise BadConfig("not set: " + ", ".join(problems))
    raw_timeout = environ.get("MAILER_TIMEOUT", "10").strip()
    try:
        timeout = float(raw_timeout)
    except ValueError:
        raise BadConfig(f"MAILER_TIMEOUT must be a number, got {raw_timeout!r}") from None
    return MailerConfig(environ["SMTP_HOST"].strip(), environ["MAILER_API_KEY"].strip(), timeout)


print(read_mailer_config({"SMTP_HOST": "smtp.example.com", "MAILER_API_KEY": "key-123", "MAILER_TIMEOUT": "2.5"}))
for env in ({}, {"SMTP_HOST": "smtp.example.com", "MAILER_API_KEY": "key-123", "MAILER_TIMEOUT": "fast"}):
    try:
        read_mailer_config(env)
    except BadConfig as e:
        print("BadConfig:", e)
```

```console
MailerConfig(smtp_host='smtp.example.com', timeout_seconds=2.5)
BadConfig: not set: SMTP_HOST, MAILER_API_KEY
BadConfig: MAILER_TIMEOUT must be a number, got 'fast'
```

Why each piece is there:

- **`environ` is a parameter.** The app calls `read_mailer_config(os.environ)`; tests pass a plain dict. That's the same dependency injection as passing `argv` into `main` in PY.M01, and no test ever has to mutate the real environment.
- **All missing names in one error.** A deploy missing three variables fails once with three names, not three times with one.
- **Blank counts as missing.** `.strip()` catches `MAILER_API_KEY=` and stray spaces or newlines from copy-pasted CI variables.
- **`field(repr=False)`** removes the key from the generated `__repr__`, so printing or logging the config doesn't leak it. Notice that the output above shows no `api_key` at all.
- **`frozen=True`**: nothing can change config at runtime by accident; assigning raises `FrozenInstanceError`.
- **`from None`** hides the internal `ValueError` so the user sees one clear message (exception chaining from PY.M04).

```quiz
{ "id": "q4", "type": "truefalse",
  "prompt": "With `api_key: str = field(repr=False)`, `print(config)` shows `api_key='***'`.", "answer": false,
  "explanation": "The field is left out of the repr entirely, as the output above shows. It's still a normal attribute: config.api_key returns the real value, so don't log that." }
```

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "A service reads `TIMEOUT = float(os.environ.get(\"TIMEOUT\", \"5\"))` at the top of a module deep in the code. In production it crashes on the first request that imports that module, with `ValueError: could not convert string to float: '5s'`. What's the better design?",
  "options": ["Validate all settings once at startup in one function, with an error that names TIMEOUT", "Wrap the float() in try/except and fall back to 5", "Read TIMEOUT inside every function that needs it", "Use int() instead of float()"], "answer": 0,
  "explanation": "Fail fast at startup, with the variable's name in the message. Silently falling back hides a broken deploy; reading it everywhere multiplies the problem." }
```

In FastAPI, build the settings in one dependency and cache it, as FastAPI's settings guide does with `@lru_cache` on `get_settings()`. Tests then override that dependency (WEB.M03). **pydantic-settings** (`BaseSettings`) automates the reading, conversion and validation, plus `.env` files with `python-dotenv`. It's a separate package that isn't installed in this academy, so here you write the boundary yourself and see exactly what it does for you.

## 4. Secrets: where they live, and what to do when one leaks

| Where | Secrets? |
|---|---|
| Source code, committed config files, Dockerfile `ENV` | Never |
| Local `.env` (in `.gitignore` and `.dockerignore`) | Yes, for your machine only |
| `.env.example` (committed) | Names and fake values only |
| CI/CD variables, the deploy platform's secret store, mounted secret files | Yes |

When a secret was committed anyway:

1. **Rotate it first**: revoke the old value at the provider and issue a new one. Deleting the line doesn't help; the value is in Git history, forks, CI logs and old images.
2. Then remove it from the code and load it from the environment.
3. Then add a guard so it doesn't happen again: a startup check like the one above, `.env` in both ignore files, and secret scanning in CI (OPS.M03).

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "You find an OAuth client secret hardcoded in a file that was pushed three months ago. What do you do first?",
  "options": ["Revoke/rotate the secret at the provider", "Delete the line and push", "Rewrite Git history to remove it", "Make the repository private"], "answer": 0,
  "explanation": "Assume it's compromised: it has been copied into history, clones, CI logs and images. Rotation is the only step that makes the old value useless. Cleaning code and history comes after." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "Suppose a Go service reads a `config/prod.yaml` committed to the repo, including the MySQL password. Propose the smallest change that passes the 12-factor litmus test without rewriting the config loader.",
  "model": "Keep the YAML for non-secret defaults, but remove credentials from it and override them from environment variables at load time (e.g. MYSQL_PASSWORD), failing at startup if they're missing. Rotate the committed password, since it's in Git history. Provide a .env.example and inject real values via the deploy system's secrets.",
  "explanation": "Secrets and per-deploy values move to the environment; rotation handles the history." }
```

## 5. Your turn

Write `load_settings(env)` for the API: required `DATABASE_URL` and `OAUTH_CLIENT_SECRET`, optional `PORT`, `DEBUG` and `LOG_LEVEL`, all validated, and a secret that never shows up in a repr or an error.

```exercise
OPS.M02.L01.E1
```
