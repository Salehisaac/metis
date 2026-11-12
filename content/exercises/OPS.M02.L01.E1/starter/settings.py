"""Typed settings for the API, read from environment variables (12-factor config)."""
from collections.abc import Mapping
from dataclasses import dataclass

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


class ConfigError(Exception):
    """Raised when the environment doesn't describe a valid configuration."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    oauth_client_secret: str
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"


def load_settings(env: Mapping[str, str]) -> Settings:
    """Build Settings from env (pass os.environ in the app, a dict in tests)."""
    raise NotImplementedError
