"""Typed settings for the API, read from environment variables (12-factor config)."""
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
    """Build Settings from env (pass os.environ in the app, a dict in tests)."""
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
