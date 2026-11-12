import importlib
import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError


def load():
    sys.modules.pop("feed_api", None)
    return importlib.import_module("feed_api")


def client_with(**settings):
    """A client whose app uses Settings(**settings) instead of the environment."""
    module = load()
    module.app.dependency_overrides[module.get_settings] = lambda: module.Settings(**settings)
    return TestClient(module.app)


def clear_env(monkeypatch):
    for name in ("FEED_PAGE_SIZE_DEFAULT", "FEED_PAGE_SIZE_MAX", "FEED_READ_ONLY"):
        monkeypatch.delenv(name, raising=False)


def test_default_page_size_comes_from_settings():
    r = client_with().get("/feed")
    assert r.status_code == 200, r.text
    assert r.json()["limit"] == 20
    assert [p["id"] for p in r.json()["items"]][:3] == [250, 249, 248]
    assert len(client_with(page_size_default=3).get("/feed").json()["items"]) == 3


def test_limit_query_parameter():
    r = client_with().get("/feed?limit=5")
    assert (r.status_code, r.json()["limit"], len(r.json()["items"])) == (200, 5, 5)


def test_limit_bounds_follow_settings():
    c = client_with(page_size_max=10)
    assert c.get("/feed?limit=10").status_code == 200
    assert c.get("/feed?limit=1").status_code == 200
    for bad in [11, 0, -3]:
        r = c.get(f"/feed?limit={bad}")
        assert r.status_code == 422, f"limit={bad}: {r.text}"
        assert r.json() == {"detail": "limit must be between 1 and 10"}


def test_non_integer_limit_is_rejected_by_fastapi():
    r = client_with().get("/feed?limit=ten")
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["query", "limit"]


def test_read_only_blocks_writes_but_not_reads():
    c = client_with(read_only=True)
    r = c.post("/feed", json={"text": "hello"})
    assert r.status_code == 503
    assert r.json() == {"detail": "feed is read-only"}
    assert c.get("/feed?limit=1").json()["items"][0]["id"] == 250, "the blocked post must not be stored"
    r = client_with(read_only=False).post("/feed", json={"text": "hello"})
    assert (r.status_code, r.json()) == (201, {"id": 251, "text": "hello"})


def test_get_settings_reads_environment(monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("FEED_PAGE_SIZE_MAX", "50")
    monkeypatch.setenv("FEED_READ_ONLY", "true")
    s = load().get_settings()
    assert (s.page_size_default, s.page_size_max, s.read_only) == (20, 50, True)


def test_get_settings_defaults_without_environment(monkeypatch):
    clear_env(monkeypatch)
    module = load()
    assert module.get_settings() == module.Settings()


def test_get_settings_is_built_once(monkeypatch):
    clear_env(monkeypatch)
    module = load()
    first = module.get_settings()
    monkeypatch.setenv("FEED_PAGE_SIZE_DEFAULT", "7")
    assert module.get_settings() is first, "settings are cached"
    module.get_settings.cache_clear()
    assert module.get_settings().page_size_default == 7


def test_invalid_environment_fails_loudly(monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("FEED_PAGE_SIZE_MAX", "lots")
    with pytest.raises(ValidationError):
        load().get_settings()
