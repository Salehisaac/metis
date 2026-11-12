"""A logging.Formatter that writes each record as one line of JSON."""
import json
import logging
from datetime import datetime, timezone

SENSITIVE = ("password", "secret", "token", "authorization")
# Attribute names every LogRecord has; anything else on a record came from extra=.
STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in vars(record).items():
            if key not in STANDARD_ATTRS:
                entry[key] = value
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        for key in entry:
            if any(word in key.lower() for word in SENSITIVE):
                entry[key] = "[REDACTED]"
        return json.dumps(entry, default=str)
