import importlib
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent


def fresh(name):
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def make_repo(capacity=2):
    db = fresh("db")
    repository = fresh("repository")
    conn = db.connect()
    conn.execute("INSERT INTO events (id, title, capacity) VALUES (1, 'PyCon meetup', ?)", (capacity,))
    return repository.RegistrationRepo(conn), conn


def client(capacity=2):
    import warnings
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient
    app = fresh("app")
    conn = fresh("db").connect()
    conn.execute("INSERT INTO events (id, title, capacity) VALUES (1, 'PyCon meetup', ?)", (capacity,))
    conn.commit()

    def override():
        with conn:
            yield conn

    # Override whichever dependency the app uses to get its connection.
    app.app.dependency_overrides[app.get_conn] = override
    return TestClient(app.app)


# --- layer rules -----------------------------------------------------------

def test_no_sql_outside_repository():
    for name in ("app.py", "service.py"):
        text = (HERE / name).read_text()
        assert not re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", text), f"{name} still contains SQL"


def test_no_fastapi_below_api_layer():
    for name in ("service.py", "repository.py"):
        assert "fastapi" not in (HERE / name).read_text(), f"{name} must not depend on FastAPI"


def test_app_calls_the_service():
    assert "service.register(" in (HERE / "app.py").read_text(), "app.py should delegate to service.register"


# --- repository ------------------------------------------------------------

def test_repo_reads_and_writes():
    repo, _ = make_repo(capacity=3)
    assert repo.get_capacity(1) == 3
    assert repo.get_capacity(99) is None
    assert repo.count_registrations(1) == 0
    assert repo.add(1, "ana@example.com") is True
    assert repo.add(1, "ana@example.com") is False
    assert repo.count_registrations(1) == 1


# --- service (no HTTP involved) ----------------------------------------------

def test_service_returns_seats_left():
    service = fresh("service")
    repo, _ = make_repo(capacity=2)
    assert service.register(repo, 1, "ana@example.com") == 1
    assert service.register(repo, 1, "bo@example.com") == 0


def test_service_unknown_event():
    service = fresh("service")
    repo, _ = make_repo()
    with pytest.raises(service.EventNotFound):
        service.register(repo, 99, "ana@example.com")


def test_service_full_event():
    service = fresh("service")
    repo, _ = make_repo(capacity=1)
    service.register(repo, 1, "ana@example.com")
    with pytest.raises(service.EventFull):
        service.register(repo, 1, "bo@example.com")


def test_service_duplicate_is_case_and_space_insensitive():
    service = fresh("service")
    repo, _ = make_repo(capacity=5)
    service.register(repo, 1, "ana@example.com")
    with pytest.raises(service.AlreadyRegistered):
        service.register(repo, 1, "  Ana@Example.COM ")


def test_service_errors_share_a_base_class():
    service = fresh("service")
    for cls in (service.EventNotFound, service.EventFull, service.AlreadyRegistered):
        assert issubclass(cls, service.RegistrationError)


# --- HTTP behaviour must not change ----------------------------------------

def test_api_created():
    r = client().post("/events/1/registrations", json={"email": " Ana@Example.com"})
    assert r.status_code == 201
    assert r.json() == {"event_id": 1, "email": "ana@example.com", "seats_left": 1}


def test_api_errors():
    c = client(capacity=1)
    assert c.post("/events/9/registrations", json={"email": "a@x.io"}).json() == {"detail": "event not found"}
    assert c.post("/events/1/registrations", json={"email": "a@x.io"}).status_code == 201
    r = c.post("/events/1/registrations", json={"email": "A@x.io"})
    assert (r.status_code, r.json()) == (409, {"detail": "event full"})


def test_api_duplicate():
    c = client(capacity=5)
    c.post("/events/1/registrations", json={"email": "a@x.io"})
    r = c.post("/events/1/registrations", json={"email": "a@x.io "})
    assert (r.status_code, r.json()) == (409, {"detail": "already registered"})
