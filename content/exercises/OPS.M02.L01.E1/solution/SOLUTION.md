```python
from collections.abc import Mapping
from dataclasses import dataclass, field

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
TRUE_WORDS = {"true", "1", "yes"}
FALSE_WORDS = {"false", "0", "no"}


class ConfigError(Exception):
    """Raised when the environment doesn't describe a valid configuration."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    oauth_client_secret: str = field(repr=False)
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"


def load_settings(env: Mapping[str, str]) -> Settings:
    values = {key: env.get(key, "").strip() for key in ("DATABASE_URL", "OAUTH_CLIENT_SECRET")}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise ConfigError(f"missing required environment variables: {', '.join(missing)}")

    port_text = env.get("PORT", "8000").strip()
    if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
        raise ConfigError(f"PORT must be an integer from 1 to 65535, got {port_text!r}")

    debug_text = env.get("DEBUG", "false").strip().lower()
    if debug_text not in TRUE_WORDS | FALSE_WORDS:
        raise ConfigError(f"DEBUG must be one of true/false/1/0/yes/no, got {debug_text!r}")

    level = env.get("LOG_LEVEL", "INFO").strip().upper()
    if level not in LOG_LEVELS:
        raise ConfigError(f"LOG_LEVEL must be one of {', '.join(LOG_LEVELS)}, got {level!r}")

    return Settings(
        database_url=values["DATABASE_URL"],
        oauth_client_secret=values["OAUTH_CLIENT_SECRET"],
        port=int(port_text),
        debug=debug_text in TRUE_WORDS,
        log_level=level,
    )
```

**Why it works**

- **Fail fast, all at once.** The required values are checked together, so a broken deploy reports every missing variable in one crash at startup instead of one per restart, and never half-starts with an empty secret.
- **Strings in, types out.** `env.get(name, default)` returns a string or the default; each optional value is converted at the boundary and rejected if it doesn't parse. `isdigit()` rules out `-1`, `8080.0` and `80a` before `int()` runs, so there's no `ValueError` to translate.
- **No guessing.** `DEBUG=on` isn't silently treated as False; a typo in production config should stop the deploy, not change behaviour.
- **The secret stays private.** `field(repr=False)` removes it from the generated `__repr__`, so `print(settings)` or a log line with `%r` doesn't leak it, and no error message interpolates it.
- **Testable.** Taking `env` as a parameter (the app calls `load_settings(os.environ)`) means tests pass plain dicts and never touch the real environment, the same dependency-injection idea as passing `argv` into `main` in PY.M01.

**Alternative:** `pydantic-settings` (`BaseSettings`) does the reading, conversion and validation declaratively, plus `.env` files with `python-dotenv`. It's a separate package (not installed here); the hand-written version shows what it does for you.
