import importlib
import logging
import re
import sys

from fastapi.testclient import TestClient


def client():
    sys.modules.pop("app", None)
    app = importlib.import_module("app").app
    return TestClient(app, raise_server_exceptions=False)


def test_generates_a_request_id_when_none_is_sent():
    c = client()
    first = c.get("/orders/1").headers.get("X-Request-ID", "")
    second = c.get("/orders/1").headers.get("X-Request-ID", "")
    assert re.fullmatch(r"[0-9a-f]{32}", first), f"expected uuid4().hex, got {first!r}"
    assert first != second, "every request needs its own ID"


def test_reuses_a_valid_incoming_request_id():
    r = client().get("/orders/1", headers={"X-Request-ID": "edge-7f3a"})
    assert r.headers.get("X-Request-ID") == "edge-7f3a"


def test_replaces_an_invalid_incoming_request_id():
    for bad in ["has space", "x" * 65, "semi;colon", ""]:
        got = client().get("/orders/1", headers={"X-Request-ID": bad}).headers.get("X-Request-ID", "")
        assert got != bad and re.fullmatch(r"[0-9a-f]{32}", got), (bad, got)


def test_log_records_carry_the_request_id(caplog):
    caplog.set_level(logging.INFO, logger="app")
    r = client().get("/orders/5", headers={"X-Request-ID": "trace-1"})
    records = [rec for rec in caplog.records if rec.name == "app"]
    assert records, "get_order should log 'order fetched'"
    assert getattr(records[-1], "request_id", None) == "trace-1" == r.headers.get("X-Request-ID")


def test_unhandled_error_returns_a_generic_500_with_the_request_id():
    r = client().get("/orders/13", headers={"X-Request-ID": "trace-2"})
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal Server Error", "request_id": "trace-2"}
    assert r.headers.get("X-Request-ID") == "trace-2", "the middleware never sees this response: set the header here"
    assert "sk_live" not in r.text, "never send exception details to the client"


def test_unhandled_error_is_logged_with_traceback_and_request_id(caplog):
    caplog.set_level(logging.INFO, logger="app")
    client().get("/orders/13", headers={"X-Request-ID": "trace-3"})
    errors = [rec for rec in caplog.records if rec.name == "app" and rec.levelno == logging.ERROR]
    assert errors, "log the failure at ERROR on the 'app' logger"
    assert errors[-1].exc_info is not None, "include the traceback (log.exception)"
    assert getattr(errors[-1], "request_id", None) == "trace-3"
    assert "/orders/13" in errors[-1].getMessage(), "say which request failed"


def test_http_exceptions_keep_their_normal_response():
    r = client().get("/orders/0", headers={"X-Request-ID": "trace-4"})
    assert (r.status_code, r.json()) == (404, {"detail": "Order not found"})
    assert r.headers.get("X-Request-ID") == "trace-4"
