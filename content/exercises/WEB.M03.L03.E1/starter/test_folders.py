import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

HERE = Path(__file__).parent
MODULES = ("main", "folders_router", "deps", "services", "repository")


def fresh(name):
    for m in MODULES:
        sys.modules.pop(m, None)
    return importlib.import_module(name)


def api():
    """A client for main.app whose repository is a new, empty one for this test only."""
    main = fresh("main")
    deps, repository = sys.modules["deps"], sys.modules["repository"]
    repo = repository.FolderRepository()
    main.app.dependency_overrides[deps.get_repository] = lambda: repo
    return TestClient(main.app)


# ---- service tests: no HTTP ----

def service(max_folders=3):
    services = fresh("services")
    return services, services.FolderService(sys.modules["repository"].FolderRepository(), max_folders=max_folders)


def test_service_creates_and_lists_by_name():
    _, s = service()
    s.create("Work")
    s.create("  family ")
    s.create("Bots")
    assert [f["name"] for f in s.list()] == ["Bots", "family", "Work"]
    assert s.get(1) == {"id": 1, "name": "Work"}


def test_service_rejects_blank_and_duplicate_names():
    services, s = service()
    s.create("Work")
    with pytest.raises(services.FolderNameTaken):
        s.create(" WORK ")
    with pytest.raises(ValueError):
        s.create("   ")


def test_service_limit_counts_existing_folders():
    services, s = service(max_folders=2)
    s.create("a")
    s.create("b")
    with pytest.raises(services.FolderLimitReached):
        s.create("c")
    s.delete(1)
    assert s.create("c")["name"] == "c", "deleting frees a slot"


def test_service_not_found():
    services, s = service()
    with pytest.raises(services.FolderNotFound):
        s.get(9)
    with pytest.raises(services.FolderNotFound):
        s.delete(9)


def test_services_module_does_not_import_fastapi():
    source = (HERE / "services.py").read_text(encoding="utf-8")
    assert "fastapi" not in source, "keep HTTP out of the service layer"


# ---- wiring ----

def test_repository_dependency_is_shared():
    deps = fresh("deps")
    assert deps.get_repository() is deps.get_repository()


def test_router_has_prefix_and_tags():
    router = fresh("folders_router").router
    assert router.prefix == "/folders"
    assert router.tags == ["folders"]


# ---- API tests ----

def test_api_create_list_get_delete():
    c = api()
    r = c.post("/folders", json={"name": "Work"})
    assert (r.status_code, r.json()) == (201, {"id": 1, "name": "Work"})
    c.post("/folders", json={"name": "bots"})
    assert [f["name"] for f in c.get("/folders").json()] == ["bots", "Work"]
    assert c.get("/folders/1").json() == {"id": 1, "name": "Work"}
    r = c.delete("/folders/1")
    assert (r.status_code, r.content) == (204, b"")
    assert c.get("/folders/1").status_code == 404


def test_api_errors():
    c = api()
    c.post("/folders", json={"name": "Work"})
    assert c.post("/folders", json={"name": "work"}).json() == {"detail": "folder name already taken"}
    assert c.get("/folders/7").json() == {"detail": "folder not found"}
    assert c.delete("/folders/7").status_code == 404
    c.post("/folders", json={"name": "a"})
    c.post("/folders", json={"name": "b"})
    r = c.post("/folders", json={"name": "c"})
    assert (r.status_code, r.json()) == (409, {"detail": "folder limit reached"})


def test_api_blank_name_is_422():
    c = api()
    r = c.post("/folders", json={"name": "   "})
    assert r.status_code == 422
    assert c.get("/folders").json() == []


def test_each_test_gets_its_own_repository():
    c = api()
    assert c.get("/folders").json() == []
    c.post("/folders", json={"name": "only here"})
    assert api().get("/folders").json() == []
