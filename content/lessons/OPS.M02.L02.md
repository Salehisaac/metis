---
{
  "id": "OPS.M02.L02",
  "title": "Logging: logger hierarchy, levels and JSON logs",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["OPS.M02.L01"],
  "objectives": [
    "Use module loggers (getLogger(__name__)) and predict which records reach a handler from the hierarchy, levels and propagation",
    "Configure logging once at the application's entry point, writing to stdout as a 12-factor event stream",
    "Pass values as lazy %-args and structured fields with extra=, and know the reserved attribute names",
    "Write a logging.Formatter subclass that emits one JSON object per line",
    "Keep secrets out of logs, and explain why redaction is only a safety net"
  ],
  "why": "When something breaks in production, logs are usually all you have. Plain print() has no levels, no logger names and no structure, so you can't filter 'errors from the payments module for request r-17' in a log system. JSON logs with consistent fields make that a query instead of a grep, and they're also where a careless line leaks a token.",
  "applications": [
    "Searchable logs in Loki, Elasticsearch or a cloud log viewer: filter by level, logger or request_id",
    "Turning on DEBUG for one noisy module without drowning in everything else",
    "Log reviews that catch tokens, passwords and full request bodies"
  ],
  "exercises": ["OPS.M02.L02.E1"],
  "sources": [
    {
      "title": "The Twelve-Factor App: XI. Logs",
      "url": "https://12factor.net/logs",
      "version": "12factor.net (current)",
      "verified": "2026-11-12",
      "claims": ["Treat logs as event streams", "The app never concerns itself with routing or storage of its output stream", "Each process writes its event stream, unbuffered, to stdout; the execution environment captures and routes it"]
    },
    {
      "title": "logging: Logging facility for Python",
      "url": "https://docs.python.org/3.12/library/logging.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["getLogger with the same name returns the same object; dotted names form a hierarchy; use __name__", "propagate (default True) passes events to ancestor loggers' handlers", "Level values NOTSET 0, DEBUG 10, INFO 20, WARNING 30, ERROR 40, CRITICAL 50; root starts at WARNING", "Logger.exception adds exception info and should only be called from an exception handler", "Keys in extra must not clash with the logging system's keys", "basicConfig does nothing if the root logger already has handlers, unless force=True", "lastResort: a StreamHandler to sys.stderr at WARNING used when no configuration exists", "LogRecord attributes: created, levelname, name, message (msg % args, set by Formatter.format), exc_info"]
    },
    {
      "title": "Logging HOWTO",
      "url": "https://docs.python.org/3.12/howto/logging.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["When to use each level; default level WARNING", "Module-level logger named __name__", "Libraries should add only a NullHandler and not log to the root logger", "Loggers, handlers, filters and formatters; formatting happens when a handler emits", "Formatting of message arguments is deferred until needed; isEnabledFor avoids expensive argument computation"]
    },
    {
      "title": "logging.handlers: StreamHandler",
      "url": "https://docs.python.org/3.12/library/logging.handlers.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["StreamHandler(stream=None) uses sys.stderr when no stream is given"]
    },
    {
      "title": "Logging Cookbook",
      "url": "https://docs.python.org/3.12/howto/logging-cookbook.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["Implementing structured logging: serialising the event as JSON (StructuredMessage example)", "Customized exception formatting with a custom formatter class, e.g. one line per event", "Filters can add contextual attributes to LogRecords"]
    },
    {
      "title": "Ruff rule G004: logging-f-string",
      "url": "https://docs.astral.sh/ruff/rules/logging-f-string/",
      "version": "Ruff docs (current); behaviour confirmed with installed ruff 0.17.3",
      "verified": "2026-11-12",
      "claims": ["G004 flags f-strings in logging calls because they are formatted eagerly even if the record is never emitted"]
    },
    {
      "title": "Command line and environment: -u and PYTHONUNBUFFERED",
      "url": "https://docs.python.org/3.12/using/cmdline.html",
      "version": "Python 3.12 (installed 3.12.3)",
      "verified": "2026-11-12",
      "claims": ["-u forces stdout and stderr to be unbuffered; PYTHONUNBUFFERED set to a non-empty string is equivalent"]
    }
  ]
}
---
## 1. Logs are an event stream

The twelve-factor rule for logs is short: **the app writes its events, unbuffered, to stdout**, and never deals with log files, rotation or shipping. Docker, Compose or the platform captures the stream and routes it to wherever logs are searched. In a container that means:

- Log to `sys.stdout` (a plain `StreamHandler()` writes to **stderr**, which Docker also captures, but pick one on purpose).
- `ENV PYTHONUNBUFFERED=1` in the Dockerfile (the same as `python -u`) so lines aren't held back in a buffer when the container dies.

Go's `log/slog` has the same pieces as Python's `logging`, under different names: you get a logger, a handler that decides where records go, and a format (text or JSON).

## 2. Loggers form a tree

Every module gets its own logger, named after the module:

```python
import logging

log = logging.getLogger(__name__)     # in shop/orders.py, the name is "shop.orders"
```

- `getLogger(name)` always returns **the same object** for the same name.
- Dotted names form a hierarchy: `shop.orders` is a child of `shop`, which is a child of the **root** logger.
- A record logged on `shop.orders` is offered to that logger's handlers, then, because `propagate` is True by default, to the handlers of every ancestor up to root.

So the usual setup is: **modules only create loggers and log; the application configures handlers once, on the root logger**, at its entry point. Libraries never add handlers, apart from an optional `NullHandler`, because configuring output is the application's decision.

Each logger can also have its own **level**. A logger without one (NOTSET) uses its nearest ancestor's level, its *effective level*:

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import logging, sys\nh = logging.StreamHandler(sys.stdout)\nh.setFormatter(logging.Formatter(\"%(name)s:%(levelname)s:%(message)s\"))\nroot = logging.getLogger()\nroot.addHandler(h)\nroot.setLevel(logging.INFO)\nlogging.getLogger(\"app.db\").setLevel(logging.WARNING)\nlogging.getLogger(\"app.db.pool\").info(\"pool ready\")\nlogging.getLogger(\"app.api\").info(\"request\")\nlogging.getLogger(\"app.db\").warning(\"slow query\")",
  "answer": "app.api:INFO:request\napp.db:WARNING:slow query",
  "explanation": "app.db.pool has no level, so it inherits WARNING from app.db and drops its INFO record. app.api inherits INFO from root. The handler lives only on root; both surviving records reach it by propagation." }
```

That's the trick for noisy libraries: `logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)` quiets one subtree and leaves the rest alone.

## 3. Levels, and what happens without configuration

| Level | Value | Use for |
|---|---|---|
| DEBUG | 10 | details for diagnosing a problem |
| INFO | 20 | confirmation that things work: started, request handled |
| WARNING | 30 | something unexpected, still working (retrying, disk filling) |
| ERROR | 40 | a function failed: this request or job didn't complete |
| CRITICAL | 50 | the program itself may not continue |

The root logger starts at **WARNING**. If nothing is configured at all, Python uses a last-resort handler that prints WARNING and above to stderr, with no level or name:

```python
import logging

log = logging.getLogger("shop.orders")
log.info("order 42 placed")
log.warning("stock low for sku-7")
```

```console
stock low for sku-7
```

The INFO line vanished. That's the classic "my logs don't show up" moment, and the fix is configuring logging at startup. `logging.basicConfig(...)` is the quick way, with a catch:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import logging, sys\nlogging.basicConfig(stream=sys.stdout, level=logging.WARNING, format=\"%(levelname)s %(message)s\")\nlogging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format=\"%(message)s\")\nlogging.info(\"hello\")\nlogging.warning(\"careful\")",
  "answer": "WARNING careful",
  "explanation": "basicConfig does nothing if the root logger already has handlers, so the second call is ignored: level stays WARNING and the first format is used. Pass force=True to replace the configuration." }
```

## 4. Pass values as arguments, not f-strings

```python
log.info("order %s placed for %s", order_id, customer_id)      # yes
log.info(f"order {order_id} placed for {customer_id}")         # works, but...
```

With `%`-style arguments, logging **defers formatting** until a handler actually emits the record. If the level filters it out, the string is never built. (The arguments themselves are still evaluated; for an expensive one, guard it with `log.isEnabledFor(logging.DEBUG)`.) The record also keeps the template (`record.msg`) and the values (`record.args`) separately, and `record.getMessage()` joins them:

```python
import logging

r = logging.LogRecord("shop", logging.INFO, "x.py", 1, "order %s", (42,), None)
print(r.msg, "|", r.getMessage())
```

```console
order %s | order 42
```

Ruff's rule G004 (`logging-f-string`) flags f-strings in logging calls for exactly this reason; you'll meet Ruff in OPS.M03.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "`log.debug(\"rows: %s\", rows)` with the logger at INFO still builds the full message string, and only then drops it.", "answer": false,
  "explanation": "The level check happens first; formatting msg % args is deferred until a handler emits the record, so a filtered DEBUG call never formats. (rows itself was already evaluated: it's an argument.)" }
```

## 5. Structured fields and a JSON formatter

Free text is hard to query. Structured logs put each value in its own field. Two stdlib pieces make that possible:

- **`extra=`** adds attributes to the `LogRecord`. `log.info("paid", extra={"order_id": 42})` gives the record an `order_id` attribute that formatters can read.
- **A `Formatter` subclass** decides how a record becomes text. Override `format(record)` and return a string.

The keys in `extra` must not clash with the record's own attributes; logging refuses:

```python
import logging

try:
    logging.getLogger("demo").warning("x", extra={"message": "boom"})
except KeyError as e:
    print("KeyError:", e)
```

```console
KeyError: "Attempt to overwrite 'message' in LogRecord"
```

Here is a small JSON formatter for the shop service. It's a different design from the exercise's: it reads only a single `fields` dict passed through `extra`:

```python
import json
import logging
import sys


class OneLineJson(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": round(record.created, 3),
            "severity": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(OneLineJson())
logging.basicConfig(level=logging.INFO, handlers=[handler])

log = logging.getLogger("shop.orders")
log.info("order %s placed", 42, extra={"fields": {"customer": "c-9", "total_cents": 1999}})
log.warning("stock low")
```

```console
{"ts": 1794500789.48, "severity": "INFO", "name": "shop.orders", "msg": "order 42 placed", "customer": "c-9", "total_cents": 1999}
{"ts": 1794500789.48, "severity": "WARNING", "name": "shop.orders", "msg": "stock low"}
```

- `record.created` is a `time.time()` float. Your timestamps will differ.
- **One JSON object per line** is what log collectors expect. `json.dumps` escapes newlines inside strings, so a multi-line message can't split an event in two.
- Tracebacks: `self.formatException(record.exc_info)` returns the traceback as a string, which you can put into a field. The cookbook's "customized exception formatting" recipe uses the same idea to keep one line per event.
- The cookbook also shows a different approach: a `StructuredMessage` object whose `__str__` renders JSON.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "In OneLineJson, why use `record.getMessage()` instead of `record.msg`?",
  "options": ["msg is the unformatted template; getMessage() applies the %-args", "msg is only set for warnings", "getMessage() adds the timestamp", "msg is a bytes object"], "answer": 0,
  "explanation": "record.msg is 'order %s placed' and record.args is (42,). getMessage() returns 'order 42 placed'." }
```

## 6. Don't log secrets

Logs are copied to more places than databases: log systems, CI output, support tickets, a teammate's terminal. Whatever you pass to the logger goes along:

```python
import logging, sys

logging.basicConfig(stream=sys.stdout, format="%(levelname)s:%(message)s")
token = "abc123"
logging.warning("using token %s", token)
```

```console
WARNING:using token abc123
```

Rules that prevent most leaks:

- Never log passwords, tokens, API keys, `Authorization` or `Cookie` headers, or whole request bodies.
- Log identifiers instead: user id, order id, request id, and the *last 4* characters of a key if you must tell keys apart.
- Log settings objects only if their secrets are excluded from `repr` (`field(repr=False)`, L01).
- **Redaction in the formatter** (replace values of fields named like `password` or `token`) is a safety net for structured fields. It can't see a secret you formatted into the message text, as above.

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "A JSON formatter redacts any field whose name contains 'token'. Which call still leaks the token?",
  "options": ["log.info(\"refresh with %s\", token)", "log.info(\"refresh\", extra={\"token\": token})", "log.info(\"refresh\", extra={\"refresh_token\": token})", "None of them"], "answer": 0,
  "explanation": "The first puts the value into the message text, where a key-name rule can't see it. The other two use field names containing 'token', so they're redacted." }
```

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "A teammate adds `logger.debug(\"settings: %r\", settings)` at startup 'to help debugging'. When is that fine and when is it a leak?",
  "model": "It's fine only if every secret field is excluded from the repr (field(repr=False)) and stays that way. Otherwise the database password and OAuth secret end up in the log stream whenever DEBUG is on, which is exactly when people paste logs into tickets. Safer: log selected non-secret fields explicitly (port, log level, database host).",
  "explanation": "Logging whole objects logs whatever their repr contains, now and after future edits." }
```

## 7. Your turn

Write `JsonFormatter.format` for the API: fixed keys `time`, `level`, `logger` and `message`, every field passed with `extra=`, the traceback when there is one, and redaction of sensitive-looking keys. Hint for later: the exercise wants *all* extra fields, not a single `fields` dict like OneLineJson, so you need a way to tell extra attributes from the standard ones.

```exercise
OPS.M02.L02.E1
```
