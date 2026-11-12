"""A logging.Formatter that writes each record as one line of JSON."""
import json
import logging
from datetime import datetime, timezone

SENSITIVE = ("password", "secret", "token", "authorization")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        raise NotImplementedError
