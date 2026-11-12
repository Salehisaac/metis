import importlib
import sys

from fastapi.testclient import TestClient

NEW = {"username": "sara", "email": "sara@example.com", "password": "s3cret-pass", "display_name": "Sara"}
PUBLIC = {"id", "username", "display_name", "bio"}


def setup():
    """Fresh module with one user created; returns (client, module)."""
    sys.modules.pop("users_api", None)
    module = importlib.import_module("users_api")
    c = TestClient(module.app)
    r = c.post("/users", json=NEW)
    assert r.status_code == 201, r.text
    return c, module


def test_create_returns_only_public_fields():
    c, _ = setup()
    r = c.post("/users", json=NEW | {"username": "omid", "bio": "hi"})
    assert r.status_code == 201
    assert r.json() == {"id": 2, "username": "omid", "display_name": "Sara", "bio": "hi"}


def test_password_is_stored_hashed_but_never_returned():
    c, module = setup()
    stored = module.users[1]
    assert stored["password_hash"] == module.fake_hash("s3cret-pass")
    assert "password" not in stored, "never store the plain password"
    for r in [c.get("/users/1"), c.patch("/users/1", json={"bio": "x"})]:
        text = r.text
        assert "password" not in text and "s3cret" not in text and stored["password_hash"] not in text


def test_read_returns_public_view():
    c, _ = setup()
    r = c.get("/users/1")
    assert r.status_code == 200
    assert r.json() == {"id": 1, "username": "sara", "display_name": "Sara", "bio": None}
    assert c.get("/users/2").status_code == 404


def test_create_requires_all_signup_fields():
    c, _ = setup()
    r = c.post("/users", json={"username": "x", "display_name": "X"})
    assert r.status_code == 422
    missing = sorted(e["loc"][-1] for e in r.json()["detail"] if e["type"] == "missing")
    assert missing == ["email", "password"]


def test_patch_changes_only_sent_fields():
    c, _ = setup()
    c.patch("/users/1", json={"bio": "backend dev"})
    r = c.patch("/users/1", json={"display_name": "Sara K"})
    assert r.status_code == 200, r.text
    assert r.json() == {"id": 1, "username": "sara", "display_name": "Sara K", "bio": "backend dev"}


def test_patch_with_empty_body_changes_nothing():
    c, module = setup()
    before = dict(module.users[1])
    r = c.patch("/users/1", json={})
    assert r.status_code == 200, r.text
    assert module.users[1] == before


def test_patch_null_bio_clears_it():
    c, _ = setup()
    c.patch("/users/1", json={"bio": "temp"})
    r = c.patch("/users/1", json={"bio": None})
    assert (r.status_code, r.json()["bio"]) == (200, None)


def test_patch_rejects_null_or_empty_display_name():
    c, module = setup()
    for bad in [None, ""]:
        r = c.patch("/users/1", json={"display_name": bad})
        assert r.status_code == 422, f"display_name={bad!r}: {r.text}"
        assert r.json()["detail"][0]["loc"] == ["body", "display_name"]
    assert module.users[1]["display_name"] == "Sara"


def test_patch_cannot_touch_protected_or_unknown_fields():
    c, module = setup()
    for field, value in [("is_admin", True), ("username", "admin"), ("password_hash", "x"), ("bio_text", "typo")]:
        r = c.patch("/users/1", json={field: value})
        assert r.status_code == 422, f"{field}: {r.text}"
        assert r.json()["detail"][0]["type"] == "extra_forbidden"
    assert module.users[1]["is_admin"] is False
    assert module.users[1]["username"] == "sara"


def test_openapi_documents_the_public_model():
    _, module = setup()
    spec = module.app.openapi()
    schema = spec["paths"]["/users/{user_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert "$ref" in schema, "declare an output model for GET /users/{user_id}"
    name = schema["$ref"].rsplit("/", 1)[-1]
    assert set(spec["components"]["schemas"][name]["properties"]) == PUBLIC
