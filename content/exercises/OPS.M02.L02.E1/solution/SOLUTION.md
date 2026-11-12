```python
import json
import logging
from datetime import datetime, timezone

SENSITIVE = ("password", "secret", "token", "authorization")
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
```

**Why it works**

- **`extra=` sets attributes on the record**, and the logging docs warn that its keys must not clash with the built-in ones. So "extra fields" = attributes a fresh `LogRecord` doesn't have. Computing that set from a real empty record (instead of typing a list) also picks up attributes newer Pythons add, such as `taskName` in 3.12.
- **`record.getMessage()`** applies the lazy `%`-args (`msg % args`). Using `record.msg` would log the template `"user %s logged in"`.
- **One line**: `json.dumps` escapes newlines inside strings, so a multi-line message or traceback can't break a log line apart, which is what log collectors need to keep one event as one record.
- **UTC ISO time** from `record.created` (a `time.time()` float) sorts correctly and needs no timezone guessing when servers sit in different regions.
- **Redaction last**, after extras and `exc` are in, so a `password` passed through `extra=` is caught too. `default=str` keeps a stray `date` or object from crashing the logging call.

**Limits and alternatives**

- Key-name redaction is a safety net, not a guarantee: a secret inside a message string (`log.info("token=%s", t)`) isn't caught. The real rule is to never pass secrets to the logger.
- The logging cookbook shows another approach: a `StructuredMessage` object whose `__str__` renders JSON, used with a plain `%(message)s` format.
