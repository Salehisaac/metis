import importlib
import io
import json
import logging
import sys
from datetime import date, datetime, timezone


def make_logger(name):
    """A logger that writes through JsonFormatter into a StringIO; returns (logger, stream)."""
    sys.modules.pop("jsonlog", None)
    jsonlog = importlib.import_module("jsonlog")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(jsonlog.JsonFormatter())
    logger = logging.getLogger(f"test.{name}")
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger, stream


def lines(stream):
    return stream.getvalue().splitlines()


def test_basic_fields_with_lazy_args():
    log, out = make_logger("basic")
    log.info("user %s logged in %d times", "ali", 3)
    entry = json.loads(lines(out)[0])
    assert entry["level"] == "INFO"
    assert entry["logger"] == "test.basic"
    assert entry["message"] == "user ali logged in 3 times"


def test_each_record_is_exactly_one_line():
    log, out = make_logger("oneline")
    log.warning("first line\nsecond line")
    log.error("next")
    got = lines(out)
    assert len(got) == 2, got
    assert json.loads(got[0])["message"] == "first line\nsecond line"


def test_time_is_iso8601_in_utc():
    log, out = make_logger("time")
    log.info("tick")
    when = datetime.fromisoformat(json.loads(lines(out)[0])["time"])
    assert when.utcoffset().total_seconds() == 0, "use UTC"
    assert abs((datetime.now(timezone.utc) - when).total_seconds()) < 60


def test_extra_fields_become_top_level_keys():
    log, out = make_logger("extra")
    log.info("order placed", extra={"request_id": "r-1", "order_id": 42})
    entry = json.loads(lines(out)[0])
    assert (entry["request_id"], entry["order_id"]) == ("r-1", 42)
    assert "args" not in entry and "msg" not in entry, "only add fields that came from extra="


def test_sensitive_fields_are_redacted():
    log, out = make_logger("redact")
    log.info("login", extra={"password": "hunter2", "api_token": "t0k", "Authorization": "Bearer x", "user": "ali"})
    raw = lines(out)[0]
    entry = json.loads(raw)
    for key in ("password", "api_token", "Authorization"):
        assert entry[key] == "[REDACTED]", key
    assert entry["user"] == "ali"
    assert "hunter2" not in raw and "t0k" not in raw


def test_exception_traceback_is_included_on_one_line():
    log, out = make_logger("exc")
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("division failed")
    got = lines(out)
    assert len(got) == 1, "the traceback must be inside the JSON string, not extra lines"
    entry = json.loads(got[0])
    assert entry["level"] == "ERROR"
    assert "ZeroDivisionError" in entry["exc"] and "Traceback" in entry["exc"]


def test_values_json_cannot_encode_become_strings():
    log, out = make_logger("default")
    log.info("report", extra={"day": date(2026, 11, 12)})
    assert json.loads(lines(out)[0])["day"] == "2026-11-12"
