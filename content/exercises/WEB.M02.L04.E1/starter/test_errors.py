import importlib
import sys

from fastapi.testclient import TestClient


def client():
    for name in ("chats_api", "errors"):
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("chats_api").app)


def test_success_responses_are_unchanged():
    c = client()
    assert c.get("/chats/1").json() == {"id": 1, "title": "Family"}
    r = c.post("/chats", json={"title": "Work"})
    assert (r.status_code, r.json()) == (201, {"id": 2, "title": "Work"})


def test_domain_error_uses_its_own_status_and_code():
    r = client().get("/chats/5")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "chat_not_found", "message": "chat 5 not found"}}


def test_unknown_route_uses_the_format():
    r = client().get("/chatz/1")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "not_found", "message": "Not Found"}}


def test_405_keeps_the_allow_header():
    r = client().put("/chats")
    assert r.status_code == 405
    assert r.json() == {"error": {"code": "method_not_allowed", "message": "Method Not Allowed"}}
    assert r.headers.get("allow") == "POST", "a 405 response MUST include Allow (RFC 9110)"


def test_raised_http_exception_uses_the_format():
    c = client()
    r = c.post("/chats", json={"title": "Family"})
    assert r.status_code == 409
    assert r.json() == {"error": {"code": "conflict", "message": "chat title already taken"}}


def test_http_exception_headers_are_kept():
    r = client().delete("/chats/1")
    assert r.status_code == 401
    assert r.json() == {"error": {"code": "unauthorized", "message": "login required"}}
    assert r.headers.get("www-authenticate") == "Bearer"


def test_unmapped_status_gets_generic_code():
    r = client().get("/teapot")
    assert (r.status_code, r.json()) == (418, {"error": {"code": "http_error", "message": "I'm a teapot"}})


def test_validation_error_lists_fields_without_input():
    r = client().post("/chats", json={"title": ""})
    assert r.status_code == 422
    assert r.json() == {"error": {
        "code": "validation_failed",
        "message": "request validation failed",
        "fields": [{"loc": "body.title", "type": "string_too_short", "message": "String should have at least 1 character"}],
    }}


def test_custom_validator_error_does_not_crash_or_echo_input():
    r = client().post("/chats", json={"title": "@secret-team"})
    assert r.status_code == 422
    assert r.json()["error"]["fields"] == [
        {"loc": "body.title", "type": "value_error", "message": "Value error, title must not start with @"}
    ]
    assert "secret-team" not in r.text, "error responses must not echo the input"


def test_several_errors_and_path_locations():
    c = client()
    r = c.get("/chats/abc")
    assert r.status_code == 422
    assert [f["loc"] for f in r.json()["error"]["fields"]] == ["path.chat_id"]
    r = c.post("/chats", json={})
    assert [(f["loc"], f["type"]) for f in r.json()["error"]["fields"]] == [("body.title", "missing")]


def test_malformed_json_is_400():
    r = client().post("/chats", content=b'{"title": "Work",}', headers={"content-type": "application/json"})
    assert r.status_code == 400
    assert r.json() == {"error": {"code": "malformed_json", "message": "request body is not valid JSON"}}
