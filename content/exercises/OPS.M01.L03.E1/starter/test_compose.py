"""Static checks on ./compose.yaml (parsed with PyYAML; Docker isn't needed)."""
import re
from pathlib import Path

import yaml

COMPOSE = Path(__file__).parent / "compose.yaml"
SECRET_KEY = re.compile(r"SECRET|PASSWORD|PASSWD|TOKEN|API_KEY", re.I)
URL_PASSWORD = re.compile(r"://[^:/@\s]+:([^@\s]+)@")


def load():
    data = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and isinstance(data.get("services"), dict), "compose.yaml needs a services: mapping"
    return data


def service(data, name):
    svc = data["services"].get(name)
    assert isinstance(svc, dict), f"service {name!r} missing (keep the names api, db and cache)"
    return svc


def environment(svc):
    """environment: as a dict, whether written as a mapping or as a list of KEY=VALUE."""
    env = svc.get("environment") or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) if "=" in item else (item, None) for item in env)
    return {k: ("" if v is None else str(v)) for k, v in env.items()}


def healthcheck_text(svc, name):
    hc = svc.get("healthcheck")
    assert isinstance(hc, dict) and hc.get("test"), f"{name} needs a healthcheck with a test"
    assert not hc.get("disable"), f"{name}'s healthcheck is disabled"
    test = hc["test"]
    if isinstance(test, list):
        assert test[0] in ("CMD", "CMD-SHELL"), f"{name}: a list test starts with CMD or CMD-SHELL, got {test[0]!r}"
        return " ".join(map(str, test[1:]))
    return str(test)


def test_images_are_pinned():
    data = load()
    for name, image in (("db", "postgres"), ("cache", "redis")):
        ref = str(service(data, name).get("image", ""))
        repo, _, tag = ref.partition(":")
        assert repo == image, f"{name} should use the official {image} image, got {ref!r}"
        assert re.match(r"^\d+", tag), f"{name}: pin a version tag like {image}:N, got {ref!r}"


def test_db_and_cache_have_healthchecks():
    data = load()
    db = healthcheck_text(service(data, "db"), "db")
    assert "pg_isready" in db, f"db: check readiness with pg_isready, got {db!r}"
    cache = healthcheck_text(service(data, "cache"), "cache")
    assert "redis-cli" in cache and "ping" in cache.lower(), f"cache: check with redis-cli ping, got {cache!r}"


def test_api_waits_for_healthy_db_and_cache():
    deps = service(load(), "api").get("depends_on")
    assert isinstance(deps, dict), "use the long depends_on syntax (a mapping) so you can set a condition"
    for name in ("db", "cache"):
        cond = (deps.get(name) or {}).get("condition")
        assert cond == "service_healthy", f"api should wait for {name} to be healthy, got condition {cond!r}"


def test_no_plaintext_secrets():
    data = load()
    for name, svc in data["services"].items():
        for key, value in environment(svc).items():
            if SECRET_KEY.search(key) and not key.endswith("_FILE"):
                assert value.startswith("${"), f"{name}.{key} is a plaintext secret; use ${{VAR}} from .env or a secret file"
            m = URL_PASSWORD.search(value)
            if m:
                assert m.group(1).startswith("${"), f"{name}.{key} has a password inside the URL; interpolate it"


def test_postgres_data_survives_in_a_named_volume():
    data = load()
    named = data.get("volumes") or {}
    mounts = service(data, "db").get("volumes") or []
    ok = []
    for m in mounts:
        if isinstance(m, dict):
            source, target = m.get("source", ""), m.get("target", "")
        else:
            source, _, rest = str(m).partition(":")
            target = rest.split(":")[0]
        if source in named and target.startswith("/var/lib/postgresql"):
            ok.append(m)
    assert ok, "mount a named volume (declared under top-level volumes:) at /var/lib/postgresql"
